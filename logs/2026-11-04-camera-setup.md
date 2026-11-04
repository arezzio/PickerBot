# Robotics Development Log — November 4, 2026

## Session Overview

**Project:** Wheeltec Robot
**Platform:** NVIDIA Jetson Orin Nano Super
**Operating System:** Ubuntu 20.04.6 LTS
**ROS Version:** ROS 1 Noetic
**Camera:** Orbbec Astra
**Robot IP:** `192.168.0.100`

### 1. Objectives

- Connect and initialize the Orbbec Astra camera.
- Verify that the color and depth camera streams are publishing.
- Verify that the camera's 3D point cloud is publishing.
- Explore viewing the live camera feed remotely from a MacBook.

### 2. Work Completed

#### A. Camera Detection and Initialization

Successfully identified and connected the Orbbec Astra camera to the Jetson.

- ROS camera package: `astra_camera`
- Package version: `1.2.7`
- Package location: `~/wheeltec_robot/src/ros_astra_camera-main`
- Launch file: `astra.launch`
- Camera serial number: `17121610203`

Command used:

```bash
roslaunch astra_camera astra.launch
```

**Result:** Camera successfully detected and initialized.

Terminal output confirmed:

```text
Found 1 devices
Device connected: (name, Astra)
(vendor, Orbbec)
Open device done, STATUS 0
Start device done
```

The camera node was running as:

```text
/camera/camera
```

#### B. ROS Camera Topics

Used the following command to identify available camera topics:

```bash
rostopic list | grep camera
```

Topics discovered:

| Topic                       | Description                                  |
| --------------------------- | -------------------------------------------- |
| `/camera/color/image_raw`   | Color camera image                           |
| `/camera/color/camera_info` | Color camera calibration information         |
| `/camera/depth/image_raw`   | Depth image                                  |
| `/camera/depth/camera_info` | Depth camera calibration information         |
| `/camera/depth/points`      | 3D point cloud                               |
| `/camera/ir/image_raw`      | Infrared image topic advertised              |
| `/camera/ir/camera_info`    | Infrared camera information topic advertised |

**Note:** The driver reported that infrared streaming would be disabled while the color stream was enabled. The IR topics being listed does not confirm that infrared images are actively publishing.

#### C. Color Image Stream Verification

Command:

```bash
rostopic hz /camera/color/image_raw
```

**Result: SUCCESS**

- Average publishing rate: approximately 29.61 FPS.
- More than 1,000 messages received during testing.
- Stable publishing rate around 30 FPS.

#### D. Depth Image Stream Verification

Command:

```bash
rostopic hz /camera/depth/image_raw
```

**Result: SUCCESS**

- Average publishing rate: approximately 29.6–29.7 FPS.
- Stable depth image publishing around 30 FPS.

#### E. 3D Point Cloud Verification

Command:

```bash
rostopic info /camera/depth/points
```

**Result:** Confirmed a publisher from `/camera/camera`.

Message type:

```text
sensor_msgs/PointCloud2
```

Then verified the publishing rate:

```bash
rostopic hz /camera/depth/points
```

**Result: SUCCESS**

- Average publishing rate: 29.94 FPS.
- 347 messages received during testing.

This confirms that the camera is actively publishing 3D point cloud data.

### 3. Remote Camera Viewing — Still in Progress

The next objective was to view the live camera feed directly from a MacBook browser while connected to the robot over Wi-Fi.

Checked whether `web_video_server` was available:

```bash
rospack find web_video_server
```

Result:

```text
/home/wheeltec/wheeltec_robot/src/web_video_server
```

The package was found in the ROS workspace.

Attempted to launch the web video server and access the camera feed through a browser. However, the live camera feed did not display successfully.

**Current status:** Troubleshooting required.

No successful remote browser visualization has been confirmed yet.

### 4. Issues and Observations

- RViz previously failed to launch through the standard SSH session because no graphical display was available.
- The web-based camera viewing setup is not yet working.
- The Astra driver reported that infrared streaming was disabled while color streaming was enabled.
- A warning about the color sensor transition was also reported during initialization; however, the color stream subsequently published successfully at approximately 30 FPS.

### 5. Next Session — Action Items

- [ ] Troubleshoot `web_video_server` startup and browser connectivity.
- [ ] Successfully display `/camera/color/image_raw` on the MacBook.
- [ ] Test viewing `/camera/depth/image_raw` through the browser.
- [ ] Explore visualizing the 3D point cloud & Lidar using RViz&#x20;
- [ ] Investigate whether color and depth data can be viewed together.
- [ ] Continue exploring the camera's capabilities for future.

### 6. Session Summary

**Overall result: Camera successfully connected and verified.**

During this session, the Orbbec Astra was successfully initialized on the Wheeltec robot. Both color and depth image streams were verified at approximately 30 FPS, and the 3D point cloud was confirmed to publish at approximately 29.94 FPS.

The main remaining task is establishing remote visualization so that camera data can be viewed directly from the MacBook.
