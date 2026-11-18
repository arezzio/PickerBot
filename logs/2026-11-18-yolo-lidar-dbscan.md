# Lab Log: 2026-11-18, YOLO Detection, LiDAR DBSCAN, and Fusion Prep

**Robot:** PickerBot Mini (Wheeltec/Roboworks)
**Host:** MacBook Air (macOS Terminal)
**Goal:** Object recognition with YOLO, compared against the LiDAR, with DBSCAN clustering the scan.
**Safety:** No motor or velocity commands were sent. Only sensor drivers and read-only scripts were run. Robot stayed on the plastic box.

## Summary

DBSCAN clustering of `/scan` works and is stable. YOLOv8n runs on the robot's GPU through TorchScript. The fusion node is written and tested offline but has not been run on the robot yet. Camera and LiDAR alignment is now known from the 2026-11-04 LiDAR log (180 degree mount) and is built into both scripts.

## Environment findings (new today)

| Item | Value | Impact |
|---|---|---|
| Python | 3.8 | Wheels downloaded on the Mac must target `--python-version 3.8` |
| CPU arch | aarch64 | Wheels must target `manylinux2014_aarch64` |
| OpenCV | 3.4.5, custom build in `~/opencv-3.4.5` | Too old to load YOLOv8 ONNX models |
| NumPy | 1.17.4 (system) | Left alone on purpose, Wheeltec nodes depend on it |
| scikit-learn | 1.3.2 in `~/.local` | Already installed. SciPy prints a NumPy version warning, DBSCAN still works |
| PyTorch | 1.14.0a0+44dac51c.nv23.02, CUDA available | Used for YOLO on the GPU |
| ONNX Runtime | Not installed | Not needed after the TorchScript route worked |

## Code added

| File | What it does |
|---|---|
| `lidar_dbscan.py` | Subscribes to `/scan`, rotates it into the robot frame, clusters with `sklearn.cluster.DBSCAN`, prints clusters once per second (size, nearest range, bearing, width) |
| `yolo_lidar_fusion.py` | Runs YOLOv8n on `/camera/color/image_raw`, converts each box's left and right edges to bearing angles, matches the nearest DBSCAN cluster inside that window, logs `~/fusion_out/detections.csv` and annotated frames |

Both are read only (subscribe only, never publish). The fusion node supports three backends: `torch` (GPU, the one that works on this robot), `opencv`, and `onnxruntime`. Both scripts were first written for ROS 2 because the manual says Humble, then ported to rospy.

## YOLO on the robot

1. Exported YOLOv8n to ONNX on the Mac (ultralytics 8.4.215, torch 2.15). **Failed:** OpenCV 3.4.5 cannot load it:
   ```
   cv2.error: OpenCV(3.4.5) .../onnx_importer.cpp:91: error: (-215:Assertion failed) ... in function 'getMatFromTensor'
   ```
2. Exported to TorchScript instead. **Works:** the file from torch 2.15 loads on the robot's torch 1.14 on CUDA despite the version gap. Output shape `[1, 84, 8400]` confirmed with a blank input.

Model on the robot: `~/models/yolov8n.torchscript` (12.4 MB). The unused `yolov8n.onnx` and a `~/wheels` folder (scikit-learn 1.3.2 for Python 3.10, wrong version) are also on the robot and can be deleted.

## DBSCAN results

Parameters: `eps = 0.12 m`, `min_samples = 5`, `max_range = 5 m`. Run before the 180 degree rotation was added, so the bearings below are raw scan angles. Robot frame = raw ± 180.

| Observation | Value |
|---|---|
| `/scan` rate | 12.00 Hz |
| Points within 5 m | about 990 to 1,030 per scan |
| Clusters per scan | 5 to 8 |
| Frame-to-frame stability (static clusters) | within about 0.01 m in range and 0.2 degrees in bearing |
| Largest cluster | about 850 points, nearest 0.41 m, raw bearing about -170 (robot frame about +10, in front), 1.6 m wide. A large surface chained into one cluster. Not identified. |
| Raw bearings seen | never inside ±60, which matches the 240 degree field of view from the 11-04 log |

**Orientation test:** stood about 1 m in front of the robot with `_max_range:=2.0`. Narrow clusters (0.07 to 0.2 m wide) appeared at about 1.0 m, raw bearing ±177, which is robot frame about 3 degrees. This confirms the 180 degree mount from the 11-04 log. Fix: both scripts now rotate the scan by `~lidar_yaw_deg` (default 180), so printed bearings are in the robot frame (0 = front, +90 = left).

## Findings worth keeping

- **The plastic box raises the LiDAR scan plane.** A small box on the floor was not seen. Test objects need to be tall: a chair, a trash can, a person.
- **False match risk in fusion.** If YOLO detects something the LiDAR cannot see, the node matches whatever is behind it. In a synthetic test an empty bearing window returned the back wall (4.06 m). Needs a sanity check (compare cluster width to box width) or must be reported as a limitation.
- **The manual is not reliable for software.** It cost time again today (ROS 2 scripts written for a ROS 1 robot). The repo logs are the source of truth. The manual's hardware specs (LiDAR model, camera field of view 63.1 x 49.4 degrees) still look right.

## Problems hit and fixes

| Problem | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: sklearn`, `--user install` error | Ran the check on the Mac inside the venv, not on the robot | Check the prompt: `MacBook-Air` vs `wheeltec@wheeltec` |
| `scp` copied old files onto themselves | Ran `scp` from the robot terminal | Run `scp` from a Mac tab (Cmd+T) |
| `ssh: Network is unreachable` mid-session | Mac auto-rejoined campus Wi-Fi | Turn off Auto-Join for other networks, or tether iPhone over USB (see 10-28 log) |
| YOLO ONNX will not load | OpenCV 3.4.5 | TorchScript on GPU |

## How to run

Mac (one time, needs internet):
```bash
cd ~/pickerbot && source yolo-env/bin/activate
yolo export model=yolov8n.pt format=torchscript imgsz=640
scp lidar_dbscan.py yolo_lidar_fusion.py wheeltec@192.168.0.100:~/
scp yolov8n.torchscript wheeltec@192.168.0.100:~/models/
```

Robot, check the model loads on the GPU:
```bash
python3 -c "import torch; m=torch.jit.load('/home/wheeltec/models/yolov8n.torchscript', map_location='cuda'); print(m(torch.zeros(1,3,640,640).cuda()).shape)"
```

Robot, Terminal 1 (LiDAR driver):
```bash
roslaunch turn_on_wheeltec_robot wheeltec_lidar.launch
```

Robot, Terminal 2 (camera driver):
```bash
roslaunch astra_camera astra.launch
```

Robot, Terminal 3:
```bash
rostopic hz /scan
python3 lidar_dbscan.py
python3 lidar_dbscan.py _max_range:=2.0 _eps:=0.10
python3 yolo_lidar_fusion.py _backend:=torch _model:=/home/wheeltec/models/yolov8n.torchscript
```

Stop anything with Ctrl+C. Results: `scp -r wheeltec@192.168.0.100:~/fusion_out .` from the Mac.

## Open items

- [ ] First fusion run on the robot. Check the inference time per frame in the log line.
- [ ] Stand 1 m in front of the camera during the fusion run. Person bearing and LiDAR leg cluster should agree. If they are off by a few degrees, set `_cam_to_lidar_yaw_deg`.
- [ ] Identify the large cluster in front of the robot (nearest 0.41 m).
- [ ] Add a width sanity check to the matcher, or document the false match limitation.
- [ ] Delete `~/wheels` and `~/models/yolov8n.onnx` on the robot.

## Next session

1. Run the fusion node with LiDAR and camera up.
2. Ground truth experiment: 3 tall objects at 1, 2, and 3 m, measured with a tape. Record YOLO detection rate, LiDAR confirmation rate, and LiDAR distance error vs the tape. This is the first results table for the symposium.
