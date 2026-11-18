#!/usr/bin/env python3
"""Step 2+3: YOLO object detection (via OpenCV DNN) checked against LiDAR DBSCAN clusters.

Read only: subscribes to camera + /scan, publishes nothing, never moves the robot.

For every detection it converts the box's left/right edges to bearing angles,
finds the DBSCAN cluster inside that bearing window, and reports the LiDAR
distance. Unmatched detections are logged too, since "camera saw it, LiDAR
did not" is part of the comparison.

Output (in ~/fusion_out):
    detections.csv   one row per detection
    frame_XXXXX.jpg  annotated frames every save_every_s seconds

ROS 1 Noetic. Run on the robot (lidar_dbscan.py must be in the same folder):
    python3 yolo_lidar_fusion.py _image_topic:=/camera/rgb/image_raw _backend:=torch _model:=~/models/yolov8n.torchscript
"""
import csv
import math
import os
import time

import cv2
import numpy as np

from lidar_dbscan import cluster_points, scan_to_points

COCO = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]


def letterbox(img, size):
    h, w = img.shape[:2]
    s = min(size / h, size / w)
    nh, nw = int(round(h * s)), int(round(w * s))
    top, left = (size - nh) // 2, (size - nw) // 2
    canvas = np.full((size, size, 3), 114, np.uint8)
    canvas[top:top + nh, left:left + nw] = cv2.resize(img, (nw, nh))
    return canvas, s, left, top


class YoloOnnx:
    """YOLOv8 model. backend="torch" runs a TorchScript export on the GPU,
    "opencv" uses cv2.dnn on an .onnx file, "onnxruntime" uses ONNX Runtime.
    Pre/post-processing (letterbox, decode, NMS) is the same for all three."""

    def __init__(self, path, size=640, conf=0.4, nms=0.45, backend="opencv"):
        self.backend = backend
        if backend == "torch":
            import torch
            self.torch = torch
            self.dev = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = torch.jit.load(path, map_location=self.dev).eval()
            with torch.no_grad():  # warm up so the first real frame is not slow
                self.model(torch.zeros(1, 3, size, size, device=self.dev))
        elif backend == "onnxruntime":
            import onnxruntime as ort
            self.sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
            self.inp = self.sess.get_inputs()[0].name
        else:
            self.net = cv2.dnn.readNetFromONNX(path)
        self.size, self.conf, self.nms = size, conf, nms

    def forward(self, blob):
        if self.backend == "torch":
            with self.torch.no_grad():
                out = self.model(self.torch.from_numpy(blob).to(self.dev))
            if isinstance(out, (list, tuple)):
                out = out[0]
            return out.float().cpu().numpy()
        if self.backend == "onnxruntime":
            return self.sess.run(None, {self.inp: blob.astype(np.float32)})[0]
        self.net.setInput(blob)
        return self.net.forward()

    def detect(self, bgr):
        img, s, dx, dy = letterbox(bgr, self.size)
        blob = cv2.dnn.blobFromImage(img, 1 / 255.0, (self.size, self.size),
                                     swapRB=True, crop=False)
        out = np.squeeze(self.forward(blob))   # (84, N); OpenCV versions add extra dims
        if out.shape[0] < out.shape[1]:
            out = out.T                         # -> (N, 4 + num_classes)
        scores = out[:, 4:]
        cls = scores.argmax(axis=1)
        conf = scores[np.arange(len(cls)), cls]
        keep = conf >= self.conf
        out, cls, conf = out[keep], cls[keep], conf[keep]
        if len(out) == 0:
            return []
        cx, cy, w, h = out[:, 0], out[:, 1], out[:, 2], out[:, 3]
        x1 = (cx - w / 2 - dx) / s
        y1 = (cy - h / 2 - dy) / s
        bw, bh = w / s, h / s
        boxes = np.column_stack((x1, y1, bw, bh)).tolist()
        idx = cv2.dnn.NMSBoxes(boxes, conf.tolist(), self.conf, self.nms)
        H, W = bgr.shape[:2]
        dets = []
        for i in np.array(idx).flatten():
            x, y, ww, hh = boxes[i]
            dets.append({
                "cls": int(cls[i]),
                "name": COCO[cls[i]] if cls[i] < len(COCO) else str(cls[i]),
                "conf": float(conf[i]),
                "x1": max(0.0, x), "y1": max(0.0, y),
                "x2": min(W - 1.0, x + ww), "y2": min(H - 1.0, y + hh),
            })
        return dets


def pixel_to_bearing(u, cx, fx):
    """Image column -> horizontal angle in camera frame. Left of centre = positive."""
    return math.atan2(cx - u, fx)


def match_detection(det, clusters, cx, fx, yaw_offset, margin):
    """Find the nearest LiDAR cluster inside the box's bearing window.

    Returns (cluster, median_distance_of_points_in_window, n_points_in_window)
    or (None, nan, 0).
    """
    b_left = pixel_to_bearing(det["x1"], cx, fx) + yaw_offset + margin
    b_right = pixel_to_bearing(det["x2"], cx, fx) + yaw_offset - margin
    best = (None, float("nan"), 0)
    for c in clusters:
        pts = c["points"]
        bear = np.arctan2(pts[:, 1], pts[:, 0])
        inside = (bear >= b_right) & (bear <= b_left)
        if not inside.any():
            continue
        d = float(np.median(np.hypot(pts[inside, 0], pts[inside, 1])))
        if best[0] is None or d < best[1]:
            best = (c, d, int(inside.sum()))
    return best


def draw(bgr, det, dist):
    x1, y1, x2, y2 = map(int, (det["x1"], det["y1"], det["x2"], det["y2"]))
    ok = not math.isnan(dist)
    color = (0, 200, 0) if ok else (0, 0, 255)
    cv2.rectangle(bgr, (x1, y1), (x2, y2), color, 2)
    label = f"{det['name']} {det['conf']:.2f} " + (f"{dist:.2f}m" if ok else "no lidar")
    cv2.putText(bgr, label, (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, color, 2)


def main():
    import rospy
    from cv_bridge import CvBridge
    from sensor_msgs.msg import CameraInfo, Image, LaserScan

    rospy.init_node("yolo_lidar_fusion")
    P = lambda name, default: rospy.get_param("~" + name, default)
    out_dir = os.path.expanduser(P("out_dir", "~/fusion_out"))
    os.makedirs(out_dir, exist_ok=True)
    yolo = YoloOnnx(os.path.expanduser(P("model", "~/models/yolov8n.onnx")),
                    P("imgsz", 640), P("conf", 0.4), backend=P("backend", "opencv"))
    bridge = CvBridge()
    state = {"scan": None, "K": None, "last_proc": 0.0, "last_save": 0.0, "frame": 0}

    csv_f = open(os.path.join(out_dir, "detections.csv"), "a", newline="")
    writer = csv.writer(csv_f)
    if csv_f.tell() == 0:
        writer.writerow(["stamp", "frame", "class", "conf", "x1", "y1", "x2", "y2",
                         "bearing_deg", "lidar_dist_m", "lidar_pts", "cluster_id",
                         "scan_age_s", "infer_ms"])

    def on_scan(msg):
        state["scan"] = msg

    def on_info(msg):
        if msg.K[0] > 0:
            state["K"] = msg.K

    def on_image(msg):
        now = time.time()
        if now - state["last_proc"] < 1.0 / P("process_hz", 3.0):
            return
        s = state["scan"]
        if s is None:
            rospy.logwarn_throttle(5, "No scan yet")
            return
        state["last_proc"] = now
        bgr = bridge.imgmsg_to_cv2(msg, "bgr8")
        H, W = bgr.shape[:2]
        if state["K"] is not None:
            fx, cx = state["K"][0], state["K"][2]
        else:
            fx = (W / 2) / math.tan(math.radians(P("hfov_deg", 63.1)) / 2)
            cx = W / 2

        t0 = time.time()
        dets = yolo.detect(bgr)
        infer_ms = (time.time() - t0) * 1000

        pts = scan_to_points(s.ranges, s.angle_min, s.angle_increment,
                             s.range_min, s.range_max, P("max_range", 6.0))
        clusters = cluster_points(pts, P("eps", 0.12), P("min_samples", 5))
        scan_age = (msg.header.stamp - s.header.stamp).to_sec()
        yaw = math.radians(P("cam_to_lidar_yaw_deg", 0.0))
        margin = math.radians(P("margin_deg", 1.0))

        summary = []
        for d in dets:
            c, dist, n_in = match_detection(d, clusters, cx, fx, yaw, margin)
            bearing = math.degrees(pixel_to_bearing((d["x1"] + d["x2"]) / 2, cx, fx))
            writer.writerow(["%.3f" % msg.header.stamp.to_sec(), state["frame"], d["name"],
                             "%.3f" % d["conf"], int(d["x1"]), int(d["y1"]),
                             int(d["x2"]), int(d["y2"]), "%.2f" % bearing,
                             "" if math.isnan(dist) else "%.3f" % dist, n_in,
                             "" if c is None else c["id"], "%.3f" % scan_age,
                             "%.0f" % infer_ms])
            draw(bgr, d, dist)
            summary.append("%s@%+.0fdeg=%s" % (d["name"], bearing,
                           "none" if math.isnan(dist) else "%.2fm" % dist))
        csv_f.flush()
        if now - state["last_save"] >= P("save_every_s", 2.0):
            state["last_save"] = now
            cv2.imwrite(os.path.join(out_dir, "frame_%05d.jpg" % state["frame"]), bgr)
        rospy.loginfo("[%.0f ms] %d clusters | %s", infer_ms, len(clusters),
                      ", ".join(summary) or "no detections")
        state["frame"] += 1

    rospy.Subscriber(P("scan_topic", "/scan"), LaserScan, on_scan, queue_size=1)
    rospy.Subscriber(P("camera_info_topic", "/camera/rgb/camera_info"), CameraInfo,
                     on_info, queue_size=1)
    rospy.Subscriber(P("image_topic", "/camera/rgb/image_raw"), Image, on_image,
                     queue_size=1, buff_size=2 ** 24)
    rospy.on_shutdown(csv_f.close)
    rospy.loginfo("Fusion node up (read only). Ctrl+C to stop.")
    rospy.spin()


if __name__ == "__main__":
    main()
