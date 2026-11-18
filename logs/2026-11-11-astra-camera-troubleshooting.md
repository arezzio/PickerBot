# Astra Camera Troubleshooting, Setup Guide

**Date:** November 11, 2026
**Robot:** Wheeltec Orin Nano Super
**Camera:** Orbbec Astra
**Operating System / ROS:** Linux / ROS Noetic (ROS 1)
**Status:** Successfully connected and streaming

## 1. Objective

Establish a working connection between the Orbbec Astra camera and the Wheeltec Orin Nano Super.

Goals:

- Connect and initialize the Astra camera.
- Configure the camera using its ROS driver.
- Establish RGB and depth image streams.
- Verify ROS camera data publishing.
- Access the live camera feed remotely from a MacBook.
- Document repeatable startup commands for the team.

## 2. Camera Hardware Information

| Property              | Value          |
| --------------------- | -------------- |
| Camera                | Orbbec Astra   |
| USB Vendor/Product ID | `2bc5:0402`    |
| Serial Number         | `17121610203`  |
| Resolution            | 640 × 480      |
| Target frame rate     | 30 FPS         |
| ROS package           | `astra_camera` |
| Launch file           | `astra.launch` |
| ROS version           | ROS Noetic     |

The camera is connected through USB and detected by Linux.

## 3. Initial Camera Setup

The Astra camera driver is located in:

```bash
~/wheeltec_robot/src/ros_astra_camera-main
```

The camera was initialized using:

```bash
roslaunch astra_camera astra.launch
```

The driver successfully detected the Astra camera and initialized its RGB, depth, and infrared sensors.

## 4. Troubleshooting Process

### A. USB Detection

We checked whether Linux recognized the camera:

```bash
lsusb
```

The Orbbec Astra was successfully detected.

### B. ROS Topic Investigation

We inspected available ROS topics:

```bash
rostopic list
```

We also checked the RGB image publisher:

```bash
rostopic info /camera/color/image_raw
```

And checked its publishing frequency:

```bash
rostopic hz /camera/color/image_raw
```

Initially, the camera topics were not consistently publishing image messages.

### C. Camera Driver Reinitialization

We restarted the Astra camera launch process:

```bash
roslaunch astra_camera astra.launch
```

After reinitialization, the camera successfully established its image streams.

### D. Remote Video Streaming

We used ROS Web Video Server to make the camera feed accessible remotely.

The initial browser streaming attempt required correcting the stream URL to use the proper ROS topic format.

The live stream was successfully displayed on a MacBook.

## 5. Camera Startup Guide

This section documents how to start the camera during future robotics sessions.

**Network information:**

- Robot IP address: `192.168.0.100`
- Web Video Server port: `8080`

### Step 1: Connect to the robot

Connect the MacBook and Wheeltec robot to the same network.

Open an SSH terminal and connect to the robot:

```bash
ssh wheeltec@192.168.0.100
```

Enter the robot's password when prompted.

### Step 2: Start the Astra camera

Open Terminal 1 on the robot.

Source the ROS workspace environment:

```bash
source ~/wheeltec_robot/devel/setup.bash
```

Start the Astra camera:

```bash
roslaunch astra_camera astra.launch
```

**Expected result:**

- Astra camera is detected.
- Camera driver initializes.
- RGB and depth streams start.
- ROS camera topics become available.

Keep this terminal running while using the camera.

*Note: The workspace setup command above assumes the catkin workspace is located at `~/wheeltec_robot`. Verify this path if the command fails.*

### Step 3: Start the Web Video Server

Open Terminal 2 on the robot.

Source the ROS environment:

```bash
source ~/wheeltec_robot/devel/setup.bash
```

Start the video server:

```bash
rosrun web_video_server web_video_server
```

The server should begin listening on port `8080`.

Keep this terminal running as well.

### Step 4: Open the live camera feed on the MacBook

Open a web browser on the MacBook and enter:

**RGB Camera Stream**

```text
http://192.168.0.100:8080/stream?topic=/camera/color/image_raw
```

The live RGB camera feed should appear in the browser.

**Important:** The MacBook and robot must be able to communicate over the network.

### Step 5: Verify camera topics

Open another terminal on the robot and source the workspace:

```bash
source ~/wheeltec_robot/devel/setup.bash
```

List the available topics:

```bash
rostopic list
```

Expected camera topics:

```text
/camera/color/camera_info
/camera/color/image_raw
/camera/depth/camera_info
/camera/depth/image_raw
/camera/depth/points
/camera/ir/camera_info
/camera/ir/image_raw
```

### Step 6: Verify publishing frequency

Check RGB image publishing:

```bash
rostopic hz /camera/color/image_raw
```

Check depth image publishing:

```bash
rostopic hz /camera/depth/image_raw
```

Check point cloud publishing:

```bash
rostopic hz /camera/depth/points
```

Expected frequency: approximately 30 Hz for each stream.

## 6. Verified Camera Topics

| ROS Topic                   | Description                 |
| --------------------------- | --------------------------- |
| `/camera/color/image_raw`   | RGB camera feed             |
| `/camera/color/camera_info` | RGB camera calibration      |
| `/camera/depth/image_raw`   | Depth image stream          |
| `/camera/depth/camera_info` | Depth camera calibration    |
| `/camera/depth/points`      | 3D depth point cloud        |
| `/camera/ir/image_raw`      | Infrared image stream       |
| `/camera/ir/camera_info`    | Infrared camera calibration |

## 7. Performance Verification

The following publishing rates were observed during testing:

| Camera Stream     | Approximate Rate |
| ----------------- | ---------------: |
| RGB image         |        29.63 FPS |
| Depth image       |        29.69 FPS |
| Depth point cloud |        29.71 FPS |

The camera successfully publishes data at approximately 30 FPS.

## 8. Troubleshooting Reference

| Problem                          | Suggested Check                                                   |
| -------------------------------- | ----------------------------------------------------------------- |
| Camera not detected              | Run `lsusb`                                                       |
| Camera launch fails              | Verify ROS workspace is sourced                                   |
| No RGB images                    | Check `rostopic info /camera/color/image_raw`                     |
| No depth images                  | Check `rostopic hz /camera/depth/image_raw`                       |
| Browser stream unavailable       | Verify Web Video Server is running                                |
| Browser cannot connect           | Check robot IP and network connectivity                           |
| Camera fails to initialize again | Inspect terminal logs before restarting or changing configuration |

## 9. Final Results

| Component                 | Status     |
| ------------------------- | ---------- |
| Astra USB detection       | Successful |
| Astra ROS driver          | Working    |
| RGB image publishing      | Successful |
| Depth image publishing    | Successful |
| 3D point cloud publishing | Successful |
| Web Video Server          | Working    |
| Remote MacBook video feed | Working    |
| Approximately 30 FPS      | Verified   |

**Final Outcome:**

The Orbbec Astra camera is successfully integrated with the Wheeltec Orin Nano Super using ROS Noetic.

The camera provides RGB, depth, and point cloud data. Its live RGB feed is accessible remotely from a MacBook through the ROS Web Video Server.

The camera integration milestone is complete.

## 10. Future Development

1. Integrate camera data into the robot's perception system.
2. Implement object detection and recognition.
3. Explore depth-based distance estimation.
4. Develop object tracking.
5. Integrate camera and LiDAR data for sensor fusion.
6. Explore autonomous navigation and obstacle avoidance.

## 11. Session Summary

The Astra camera troubleshooting and integration process was successful.

The team verified USB detection, initialized the ROS camera driver, resolved image publishing issues, configured remote video streaming, and confirmed RGB, depth, and point cloud publishing rates.

**Milestone achieved: Astra camera successfully integrated and streaming through ROS Noetic.**

Start the Astra camera
TERMINAL 1 — CAMERA DRIVER
source ~/wheeltec_robot/devel/setup.bash
roslaunch astra_camera astra.launch



TERMINAL 2 — VIDEO SERVER
source ~/wheeltec_robot/devel/setup.bash
rosrun web_video_server web_video_server



MACBOOK — BROWSER
http://192.168.0.100:8080/stream?topic=/camera/color/image_raw
