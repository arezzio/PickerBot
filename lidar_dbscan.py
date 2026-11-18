#!/usr/bin/env python3
"""Step 1: cluster the 2D LiDAR scan with DBSCAN and print the clusters.

Read only: subscribes to /scan, publishes nothing, never moves the robot.

ROS 1 Noetic. Run on the robot (after the LiDAR driver is up):
    python3 lidar_dbscan.py
    python3 lidar_dbscan.py _eps:=0.10 _min_samples:=4

Bearing convention (ROS REP 103): 0 deg = straight ahead, positive = left.
"""
import math

import numpy as np
from sklearn.cluster import DBSCAN


def scan_to_points(ranges, angle_min, angle_increment, range_min, range_max,
                   max_range=None):
    """LaserScan arrays -> Nx2 array of (x forward, y left) in metres."""
    r = np.asarray(ranges, dtype=np.float64)
    ang = angle_min + np.arange(r.size) * angle_increment
    hi = range_max if max_range is None else min(range_max, max_range)
    ok = np.isfinite(r) & (r > range_min) & (r < hi)
    r, ang = r[ok], ang[ok]
    return np.column_stack((r * np.cos(ang), r * np.sin(ang)))


def cluster_points(points, eps=0.12, min_samples=5):
    """Run sklearn DBSCAN. Returns clusters sorted nearest first.

    eps is the neighbour radius in metres, min_samples the points needed
    to form a core point. Label -1 (noise) is dropped.
    """
    if len(points) < min_samples:
        return []
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(points)
    clusters = []
    for k in sorted(set(labels) - {-1}):
        pts = points[labels == k]
        cx, cy = pts.mean(axis=0)
        dist = np.hypot(pts[:, 0], pts[:, 1])
        bear = np.arctan2(pts[:, 1], pts[:, 0])
        clusters.append({
            "id": int(k),
            "n": int(len(pts)),
            "points": pts,
            "centroid": (float(cx), float(cy)),
            "range": float(math.hypot(cx, cy)),
            "nearest": float(dist.min()),
            "bearing": float(math.atan2(cy, cx)),
            "bearing_min": float(bear.min()),
            "bearing_max": float(bear.max()),
            "width": float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0))),
        })
    clusters.sort(key=lambda c: c["nearest"])
    return clusters


def main():
    import rospy
    from sensor_msgs.msg import LaserScan

    rospy.init_node("lidar_dbscan")
    topic = rospy.get_param("~scan_topic", "/scan")
    last = [0.0]

    def on_scan(msg):
        now = rospy.get_time()
        if now - last[0] < 1.0:
            return
        last[0] = now
        eps = rospy.get_param("~eps", 0.12)
        ms = rospy.get_param("~min_samples", 5)
        pts = scan_to_points(msg.ranges, msg.angle_min, msg.angle_increment,
                             msg.range_min, msg.range_max,
                             rospy.get_param("~max_range", 5.0))
        clusters = cluster_points(pts, eps, ms)
        half = math.radians(rospy.get_param("~front_fov_deg", 360.0)) / 2
        clusters = [c for c in clusters if abs(c["bearing"]) <= half]
        lines = ["%d pts -> %d clusters (eps=%s, min_samples=%s)"
                 % (len(pts), len(clusters), eps, ms)]
        for c in clusters[:8]:
            lines.append("  #%-3d n=%-4d nearest=%.2f m  bearing=%+6.1f deg  width=%.2f m"
                         % (c["id"], c["n"], c["nearest"],
                            math.degrees(c["bearing"]), c["width"]))
        rospy.loginfo("\n".join(lines))

    rospy.Subscriber(topic, LaserScan, on_scan, queue_size=1)
    rospy.loginfo("Listening on %s (read only). Ctrl+C to stop.", topic)
    rospy.spin()


if __name__ == "__main__":
    main()
