# LiDAR, Obstacle Tracking, and Robotic Arm — November 18, 2026

### 1. Objectives

Today's session focused on:

- Identifying and verifying the mounted LiDAR hardware.
- Establishing communication between the LiDAR and ROS Noetic.
- Configuring and launching the obstacle-tracking node.
- Verifying published obstacle-position data.
- Investigating the robotic arm's ROS package, software architecture, and control system.
- Beginning RViz visualization setup.

---

### 2. LiDAR Hardware Identification and Configuration

Identified the mounted LiDAR as the **LSLiDAR M10-P**.

Verified the serial device assignments:

- `/dev/wheeltec_lidar` → `/dev/ttyCH343USB0`
- `/dev/wheeltec_controller` → `/dev/ttyCH343USB1`

Located the ROS driver package:

`~/wheeltec_robot/src/lsx10/lslidar_driver`

Launched the LiDAR using:

```bash
source ~/wheeltec_robot/devel/setup.bash

roslaunch turn_on_wheeltec_robot wheeltec_lidar.launch rplidar_mode:=ls_M10P_uart
```

The driver successfully initialized:

```text
Lidar is M10_P
port = /dev/wheeltec_lidar, baud_rate = 500000
open_port /dev/wheeltec_lidar OK !
Initialised lslidar without error
```

### 3. LiDAR Data Verification

Verified that the LiDAR publishes data through the `/scan` ROS topic.

Commands used:

```bash
rostopic list | grep scan
rostopic hz /scan
rostopic echo -n 1 /scan
```

Results:

- Scan topic: `/scan`
- Publishing frequency: approximately 12 Hz
- Message type: `sensor_msgs/LaserScan`
- Frame ID: `laser`
- Angular coverage: approximately 360 degrees (-π to +π)
- Valid distance measurements received.

**Result:** Confirmed that the LSLiDAR M10-P successfully publishes live LaserScan data.

---

### 4. Obstacle Tracking Configuration

Located the existing obstacle-tracking script:

`~/wheeltec_robot/src/simple_follower/scripts/laserTracker.py`

Inspected the script and its launch configuration.

The tracker:

- Subscribes to the LiDAR `/scan` topic.
- Compares consecutive LiDAR scans to filter potentially noisy measurements.
- Searches for the closest plausible distance measurement.
- Publishes the selected point's angle and distance.

Launch parameters:

| Parameter   | Value |
| ----------- | ----: |
| `winSize`   |     2 |
| `deltaDist` |   0.2 |

Verified the custom ROS message:

```text
float32 angleX
float32 angleY
float32 distance
```

Message type: `simple_follower/position`

Started the obstacle tracker:

```bash
roslaunch simple_follower laserTracker.launch
```

The node successfully started as:

`/laser_tracker`

### 5. Obstacle Tracking Verification

Confirmed that the following topics were created:

```text
/object_tracker/current_position
/object_tracker/info
```

Verified that `/laser_tracker` publishes to:

`/object_tracker/current_position`

Checked the publishing frequency:

```bash
rostopic hz /object_tracker/current_position
```

**Observed publishing rate: approximately 12 Hz.**

Retrieved three consecutive position messages:

```yaml
angleX: -1.4643
angleY: 42.0
distance: 0.432
```

```yaml
angleX: -1.5510
angleY: 42.0
distance: 0.429
```

```yaml
angleX: -1.5981
angleY: 42.0
distance: 0.429
```

These measurements demonstrate consistent selection of a nearby LiDAR return at approximately 0.43 meters.

**Result:** Successfully verified the obstacle-tracking pipeline from raw LiDAR measurements to processed position messages.

Note: The existing tracker identifies a plausible closest LiDAR point. It does not yet perform complete object recognition or obstacle classification. The physical source of the approximately 0.43-meter return has not yet been confirmed.

---

### 6. Robotic Arm Software Investigation

Investigated the robotic arm's dedicated ROS workspace:

`~/wheeltec_arm/src/stepper_arm`

Confirmed that ROS can locate the package:

```bash
rospack find stepper_arm
```

Output:

```text
/home/wheeltec/wheeltec_arm/src/stepper_arm
```

Inspected the available source files and project structure.

Important files identified:

| File                         | Purpose                                          |
| ---------------------------- | ------------------------------------------------ |
| `stepper_motor_arm.cpp`      | Arm joint calculations and control-related logic |
| `robot_keyboard_control.cpp` | Keyboard-based arm control                       |
| `Arm_P_I_Solution.py`        | Arm inverse-kinematics solution                  |
| `auto_pick_colorBlock.cpp`   | Automatic color-block picking logic              |
| `position.msg`               | Custom position message definition               |

Also identified the following launch files:

- `arm_cam.launch`
- `color_block_grab.launch`
- `keyboard_control.launch`

#### 6.1 Arm Joint Configuration and Kinematics

Inspected the arm's software configuration and inverse-kinematics logic.

The arm control software represents three joints and a gripper:

- Joint A
- Joint B
- Joint C
- Gripper

The inspected software includes the following joint limits:

| Joint | Minimum (radians) | Maximum (radians) |
| ----- | ----------------: | ----------------: |
| A     |              -1.9 |               1.9 |
| B     |             -0.17 |            1.5708 |
| C     |            0.3918 |            2.2981 |

The software also includes workspace and kinematics calculations used to determine possible arm positions.

#### 6.2 Keyboard Control Investigation

Inspected `robot_keyboard_control.cpp` to understand how manual arm control is designed.

The keyboard control logic uses:

- Joint movement increments of approximately 0.02 radians.
- Position adjustments of approximately 1 cm.
- Gripper adjustments of approximately 5 units.
- Four command values representing joints A, B, C, and the gripper.

The keyboard controller publishes a `std_msgs/Float32MultiArray` containing:

```text
[joint_A, joint_B, joint_C, gripper]
```

The command topic is:

`arm_cmd`

#### 6.3 Arm Communication Investigation

Investigated where `arm_cmd` is used throughout the robot's software.

Found references to `arm_cmd` in:

- `robot_keyboard_control.cpp`
- `auto_pick_colorBlock.cpp`
- The `JointStates_topic` parameter in `wheeltec_robot.cpp`

Also inspected the robot's serial communication code.

The investigation identified STM32 serial communication associated with the robot controller through:

`/dev/wheeltec_controller`

However, the inspection did not establish a confirmed subscriber or hardware driver that receives the arm's `arm_cmd` messages and sends corresponding commands to the physical arm motors.

**Current result:** The arm's software architecture, joint configuration, kinematics, and command-publishing logic have been investigated. Physical motor communication and actual arm movement have not yet been verified.

---

### 7. RViz Visualization — Troubleshooting

Confirmed that RViz is installed:

```bash
rospack find rviz
```

Output:

```text
/opt/ros/noetic/share/rviz
```

Attempted to launch RViz through SSH:

```bash
rviz
```

Encountered the following error:

```text
qt.qpa.xcb: could not connect to display
Could not load the Qt platform plugin "xcb"
```

Investigated the display configuration and determined:

- The robot's SSH session had an empty `$DISPLAY` variable.
- X11 forwarding is enabled in `/etc/ssh/sshd_config`.
- `xauth` is installed at `/usr/bin/xauth`.
- XQuartz was installed and successfully launched on the MacBook.
- A new SSH connection was established using `ssh -Y`.
- SSH debugging identified the issue:

```text
X11 forwarding requested but DISPLAY not set
```

The graphical display connection remains unresolved.

---

### 8. Next Steps

#### LiDAR and Obstacle Tracking

1. Configure the MacBook's `DISPLAY` environment variable for XQuartz.
2. Verify local XQuartz communication.
3. Reconnect to the robot using SSH with X11 forwarding.
4. Confirm that the robot receives a valid `$DISPLAY` value.
5. Launch RViz and visualize the `/scan` LaserScan topic.
6. Configure RViz to use `laser` as the Fixed Frame.
7. Investigate visualization of `/object_tracker/current_position`.
8. Inspect obstacle-avoidance message compatibility before attempting integration.

#### Robotic Arm

1. Continue investigating the arm's command-publishing and receiving architecture.
2. Identify the physical arm motor controller and its communication interface.
3. Determine whether an arm-command subscriber or driver exists in another package or workspace.
4. Investigate how the arm's keyboard controller communicates with the physical hardware.
5. Verify the ROS master and required nodes before attempting arm tests.
6. Test arm movement and gripper operation only after confirming the hardware communication path and safe operating conditions.
7. Continue investigating the automatic color-block picking system.

---

### 9. Current Progress Summary

| Component                          | Status                        |
| ---------------------------------- | ----------------------------- |
| LSLiDAR M10-P identification       | Completed                     |
| LiDAR serial communication         | Working                       |
| ROS Noetic LiDAR driver            | Working                       |
| `/scan` publishing                 | Verified (\~12 Hz)            |
| `laserTracker.py`                  | Running                       |
| Position message publishing        | Verified (\~12 Hz)            |
| Obstacle-position measurements     | Verified                      |
| RViz installation                  | Confirmed                     |
| RViz graphical display             | Troubleshooting               |
| Arm ROS package identification     | Completed                     |
| Arm source-code investigation      | Completed for inspected files |
| Joint configuration and kinematics | Investigated                  |
| Keyboard-control software          | Investigated                  |
| Arm command topic (`arm_cmd`)      | Identified                    |
| Physical arm communication         | Not yet verified              |
| Physical arm movement              | Not yet tested                |
| Automatic color-block picking      | Not yet tested                |
| Obstacle-avoidance integration     | Not yet tested                |

### 10. Overall Achievement

Today's session established a working LiDAR perception pipeline on the Wheeltec Orin Nano Super using ROS Noetic. The LSLiDAR M10-P was successfully initialized, and live 360-degree LaserScan measurements were verified at approximately 12 Hz. The existing obstacle-tracking node was also launched and confirmed to publish position messages at approximately the same rate.

Additionally, the robotic arm's software architecture was investigated, including its three-joint configuration, gripper, inverse-kinematics calculations, keyboard controls, and command-publishing structure. The investigation helped identify an important next step: understanding how the arm's ROS commands connect to its physical motor controller.

The next phase will focus on RViz visualization, further investigation of the arm's hardware communication, and eventually testing obstacle avoidance and robotic arm functionality once their respective control paths are verified.

