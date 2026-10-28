# Lab Log: 2026-10-28, First Connection and Bringup

**Robot:** PickerBot Mini (Roboworks / Wheeltec)
**Host:** MacBook Air (macOS Terminal)
**Goal:** Connect to the robot, verify the software stack and sensors, run a first motion test with wheels off the ground.
**Result:** Full stack working. Mac to Wi-Fi, SSH, ROS master, STM32, and all four motors respond correctly in every direction.

## System facts (verified on the robot)

| Item | Value |
|---|---|
| Compute | NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super |
| OS | Ubuntu 20.04.6 LTS, kernel 5.10.216-tegra, L4T 35.6.1 |
| ROS | **ROS 1 Noetic** (rosversion 1.17.0) |
| Workspaces sourced in `~/.bashrc` | `wheeltec_robot`, `wheeltec_arm`, `wheeltec_lidar`, `cartographer_ws`, Autoware |
| ROS master | `ROS_MASTER_URI=http://192.168.0.100:11311` |
| Robot IP | 192.168.0.100 (robot hosts its own Wi-Fi hotspot) |
| System clock | Not set (boots at 1970-01-01). ROS timestamps are seconds since boot. |

## Discrepancies with the User Manual (v20250910)

| Manual says | Robot actually has | Impact |
|---|---|---|
| ROS 2 Humble, `ros2 launch ...` | ROS 1 Noetic, `ros2` command not found | Use ROS 1 commands (`roslaunch`, `rostopic`). ROS 2 tutorials do not apply directly. |
| Bringup file `turn_on_wheeltec_robot.launch.py` | `turn_on_wheeltec_robot.launch` | Section 11's `roslaunch` line is the correct one for this robot. |
| Run `wheeltec_udev.sh` before first use | udev rules already installed | No action needed. |
| Battery 6000 mAh | `robot_BatteryCapacity: 5000` in bringup params | Only affects battery percentage estimate. |
| Wheeltec notes: arm config in `wheeltec_arm/src/wheeltec_arm_pick/launch/base_serial.launch` | File does not exist at that path | Locate before arm work. |

## Problems hit and fixes

**1. `ssh: connect to host 192.168.0.100 port 22: Operation timed out`**
Cause: Mac was on campus Wi-Fi, not the robot hotspot. The robot hotspot has no internet, so macOS auto-rejoins other networks.
Check: `ipconfig getifaddr en0` must return `192.168.0.x`.
Fix: Join the robot network. For internet at the same time, tether an iPhone over USB and put "iPhone USB" above Wi-Fi in System Settings > Network > Set Service Order.

**2. No serial devices, STM32 not visible to the Jetson**
Cause: The USB hub (cable tagged `USB拓展坞`) was not plugged into the Jetson. The STM32, LiDAR, and gripper RGB camera all connect through that hub.
Diagnosis: `lsusb` showed only onboard devices; `sudo dmesg -w` showed the devices appear the moment the hub was plugged in.
Fix: Plug the hub cable into a Jetson USB-A port.

Cable labels on the robot: `深度相机` = depth camera, `RGB相机` = RGB camera, `USB拓展坞` = USB hub, `充电口` = charging port.

## USB topology (after fix)

| Device | USB ID | Connection | Linux device |
|---|---|---|---|
| Orbbec Astra S depth camera | `2bc5:0402` | Direct to Jetson | (UVC / OpenNI) |
| USB 2.0 hub | `1a40:0101` | Direct to Jetson | |
| STM32 controller (WCH CH9102) | `1a86:55d4` | Via hub | `/dev/ttyCH343USB1` -> `/dev/wheeltec_controller` |
| LiDAR serial (WCH CH9102) | `1a86:55d4` | Via hub | `/dev/ttyCH343USB0` -> `/dev/wheeltec_lidar` |
| Gripper RGB camera ("Integrated Webcam") | `0bda:3031` | Via hub | UVC video device |

Note: `lsusb` mislabels the Astra as "Realtek Bluetooth Radio". Vendor ID `2bc5` is Orbbec.

## Configuration in launch files (factory defaults, unchanged)

| Parameter | File | Value |
|---|---|---|
| `car_mode` | `turn_on_wheeltec_robot.launch` | `senior_mec_bs` |
| `rplidar_mode` | `wheeltec_lidar.launch` | `ls_M10P_uart` (matches manual) |
| `camera_mode` | `wheeltec_camera.launch` | `Astra_S` (gripper RGB cam not included) |
| `usart_port_name` | bringup params | `/dev/wheeltec_controller` |
| `serial_baud_rate` | bringup params | 115200 |

`car_mode` in ROS selects the URDF and sensor transforms. Wheel kinematics run in the STM32 firmware.

## Bringup

```
roslaunch turn_on_wheeltec_robot turn_on_wheeltec_robot.launch
```
Key log lines: `wheeltec_robot serial port opened`, `Odom sensor activated`, `Imu sensor activated`. URDF inertia warning is harmless.

Topics published:
```
/PowerVoltage  /arm_cmd  /cmd_vel  /imu  /joint_states  /odom
/robot_pose_ekf/odom_combined  /rosout  /rosout_agg  /tf  /tf_static
```
Topics that move hardware: `/cmd_vel` (wheels), `/arm_cmd` (arm).

## Sensor checks (robot stationary)

| Check | Result | Notes |
|---|---|---|
| `/PowerVoltage` | 23.10 V | Manual: 25.55 V full, 16.5 V cutoff. About 3.3 V/cell, mid LFP plateau. |
| `/imu` angular velocity | ~0 on all axes | Healthy |
| `/imu` linear acceleration | x 0.016, y 0.022, z 9.41 m/s² | Level. z reads ~4% below 9.81, small accel calibration offset. |
| `/imu` rate | 20.0 Hz, very stable | Upper bound for any control loop using IMU data. |
| `/cmd_vel` publishers | None. Subscriber: `/wheeltec_robot` | Nothing else commanding the wheels. |

## Motion test

Robot on plastic box, wheels in the air.
```
roslaunch wheeltec_robot_rc keyboard_teleop.launch
```
Result: All four mecanum wheels responded correctly in all directions.

## Safety procedure used

1. Robot on plastic box, wheels clear of box edges and loose wires.
2. Read-only commands (`rostopic list/echo/hz/info`) before anything that publishes velocity.
3. Stop options: `k` or space in teleop, Ctrl+C to quit teleop, STM32 enable switch off as hardware stop.

## Shutdown procedure

1. Ctrl+C teleop, then Ctrl+C bringup.
2. `sudo shutdown now`, wait for the Jetson to finish.
3. Then switch off power.

Reason: boot log showed `EXT4-fs: 4 orphan inodes deleted / recovery complete`, which suggests previous unclean power-offs.

## Open items

- [ ] Confirm `car_mode: senior_mec_bs` is correct for PickerBot Mini (ask Dr. Bui, check STM32 OLED model name).
- [ ] Decide whether `camera_mode` should be `Astra_S+RgbCam` for grasping work.
- [ ] Find where the arm workspace sets its robot model.
- [ ] Discuss with Dr. Bui: stay on ROS 1 Noetic or plan a ROS 2 migration.
- [ ] Charge battery.
- [ ] Plan time sync if host-side ROS nodes are added (robot clock not set).

## Next session

1. Read-only: launch LiDAR, confirm `/scan` publishes near 12 Hz.
2. Read-only: view the depth camera stream.
3. First floor drive at reduced speed, wide clear area, someone at the enable switch.

## Command reference

```
# Mac
ipconfig getifaddr en0              # confirm on robot network (192.168.0.x)
ping -c 3 192.168.0.100             # robot reachable?
ssh wheeltec@192.168.0.100          # credentials: see User Manual section 10.6

# Robot, hardware
cat /proc/device-tree/model; echo   # board model
lsusb                               # USB devices
ls -l /dev/wheeltec* /dev/ttyCH343USB*
sudo dmesg -w                       # live kernel messages (Ctrl+C to stop)

# Robot, ROS 1
roslaunch turn_on_wheeltec_robot turn_on_wheeltec_robot.launch
rostopic list
rostopic echo -n 1 /PowerVoltage
rostopic echo -n 1 /imu
rostopic hz /imu
rostopic info /cmd_vel
roslaunch wheeltec_robot_rc keyboard_teleop.launch
```
