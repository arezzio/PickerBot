# Lab Log: 2026-11-04, LiDAR Bringup and Characterization

**Robot:** PickerBot Mini (Wheeltec/Roboworks)
**Goal:** Get the LiDAR publishing in ROS and verify its data, frame, and field of view.
**Safety:** No motor or velocity commands were sent. Only the LiDAR driver and read-only tools were run. Robot stayed on the plastic box.

## Summary

The LiDAR works. It is a Leishen M10P on serial at 500000 baud, publishing `/scan` at 12 Hz with about 1,667 points per scan. It is mounted rotated 180 degrees, and the driver masks the rear, giving a 240 degree field of view centered on the robot's front.

## Environment findings


- `~/.bashrc` already sources Noetic and all workspaces (`wheeltec_robot`, `wheeltec_arm`, `wheeltec_lidar`, `cartographer_ws`, `.autoware`) on login. **Do not manually source `/opt/ros/noetic/setup.bash`**, because it resets the package path and hides the Wheeltec packages. If that happens, exit and SSH back in.
- `ROS_MASTER_URI` is `http://192.168.0.100:11311`, so anyone SSH'd into the robot shares the same ROS master.
- The robot clock is unset (shows 1970) because its hotspot has no internet. Harmless for now, but it can cause confusing timestamps.

## Hardware and devices

| Item | Value |
|---|---|
| LiDAR model | Leishen M10P (confirmed from sticker) |
| LiDAR device | `/dev/wheeltec_lidar -> ttyCH343USB0` |
| Chassis controller device | `/dev/wheeltec_controller -> ttyCH343USB1` |
| Baud rate | 500000 |
| Packet header | `A5 5A` (seen in raw bytes at 500000 baud) |

## How to run

Terminal 1 (driver only, no chassis or motors):
```bash
roslaunch turn_on_wheeltec_robot wheeltec_lidar.launch
```
The default `rplidar_mode` is `ls_M10P_uart`, which is correct. No override needed.

Terminal 2 (checks):
```bash
rostopic hz /scan
rostopic echo -n 1 /scan
python3 ~/scan_test.py
```

**Only one person should run the driver at a time.** Two readers on the serial port garble the data.

## Troubleshooting history

1. `RLException: wheeltec_lidar.launch is neither a launch file...`, caused by manually re-sourcing Noetic. Fixed with a fresh SSH session.
2. First launch with the default M10P mode printed repeated `error` lines, then crashed with `free(): invalid pointer`. That run did not auto-start a ROS master, meaning one was already running, likely from a second session. A second reader on the port is the most likely cause.
3. `ls_M10P_PLUS_uart` mode (921600 baud) launched quietly but published no messages. Wrong protocol for this unit.
4. Raw byte check across baud rates showed structured data only at 500000 (`A5 5A` header, smoothly varying 16-bit values). No `7B ... 7D` chassis frames at 115200, so the device links are not swapped.
5. Relaunched the default M10P mode with the port free: no errors, 12 Hz.

Raw byte check used (read only, stop the driver first):
```bash
for b in 115200 230400 460800 500000 921600; do echo "== $b"; stty -F /dev/wheeltec_lidar $b raw -echo; timeout 1 cat /dev/wheeltec_lidar | xxd | head -4; done
```

## Verified measurements

| Property | Value |
|---|---|
| Scan rate | 12 Hz (matches manual) |
| Points per scan | about 1,667 (about 20,000 samples/s, matches manual) |
| Minimum range | 0.15 m (`min_range` param); anything closer is invalid |
| `max_range` param | 100.0 |
| Valid points per scan | about 950 to 1,030 in a normal room |

## Frame and field of view

- **Mounting:** `robot_model_visualization.launch` publishes `base_footprint -> laser` with yaw `3.14` for every 2D LiDAR model. In the raw `/scan` message, **0 degrees points out the robot's back** and the robot's front is at plus or minus 180.
- **Conversion to robot frame:** `robot_angle = (scan_angle_deg + 360) % 360 - 180`
- **Field of view in robot frame:** minus 120 to plus 120 degrees (240 degree arc centered on the front). The rear wedge is masked by the driver (`truncated_mode: 1`, `disable_min: [120]`, `disable_max: [240]`). Confirmed by walking around the robot: readings never exceeded plus or minus 120 and pinned at the boundary when behind it.
- **Sign convention (verified, robot's point of view):** 0 = front, +90 = robot's left, -90 = robot's right. Matches standard ROS (counterclockwise positive). No sign flip needed.

## Test script (`~/scan_test.py` on robot)

Prints the closest valid return each scan, with the angle in the robot frame.

```python
import math, rospy
from sensor_msgs.msg import LaserScan

def cb(m):
    pts = [(r, i) for i, r in enumerate(m.ranges) if m.range_min < r < m.range_max]
    if not pts:
        return print('no valid points')
    r, i = min(pts)
    ang = (math.degrees(m.angle_min + i * m.angle_increment) + 360) % 360 - 180
    print(f'closest {r:.2f} m at {ang:.0f} deg, {len(pts)}/{len(m.ranges)} valid')

rospy.init_node('scan_test')
rospy.Subscriber('/scan', LaserScan, cb, queue_size=1)
rospy.spin()
```

## Implications for the research

- Code that reads raw `/scan` ranges directly (for example, as RL policy input) must apply the 180 degree correction. ROS navigation handles it through TF.
- The Gazebo LiDAR model must match: same 180 degree mount, same 240 degree field of view, same 0.15 m minimum range. Otherwise sim-to-real will break quietly.
- The 0.15 m blind zone matters for obstacle avoidance rewards and safety stops.

## Open items

- [ ] Agree on a one-driver rule when two people are connected to the robot.
