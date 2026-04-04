"""
================================================================================
DAgger-lite Data Collector

* Purpose: ROS 2 node for Dataset Aggregation (DAgger). It synchronously records 
           LiDAR and velocity data ONLY when the robot is near obstacles, 
           capturing expert corrections in dangerous states.
           Includes thread safety, I/O buffering, and stale command prevention.
* Inputs:  - /scan (sensor_msgs/LaserScan)
           - /cmd_vel (geometry_msgs/Twist)
* Outputs: - CSV file: [scan_1, ..., scan_N, linear_x, angular_z]
* Args:    - --downsample (int): Target LiDAR array size (default: 180)
           - --rate (int): Loop frequency in Hz (default: 20)
           - --out (str): Output CSV file path
           - --max_range (float): Max LiDAR range (default: 3.5)
           - --danger_dist (float): Distance threshold to trigger recording (default: 0.6)
           - --cooldown (int): Steps to wait between logs to prevent flooding (default: 5)
* Usage:   python3 data_collector_DAgger.py --out logs/dagger.csv --danger_dist 0.8
================================================================================
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
import numpy as np
import csv
import os
import argparse
import time
import threading
from datetime import datetime


def clamp_scan(ranges: list, max_range: float = 3.5) -> np.ndarray:
    """Handle NaN/Inf values and clip ranges using fast numpy vectorization."""
    arr = np.array(ranges, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=max_range, posinf=max_range, neginf=0.0)
    return np.clip(arr, 0.0, max_range)


class DAggerCollector(Node):
    def __init__(
        self,
        downsample=180,
        rate_hz=20,
        out_file='logs/dagger_dataset.csv',
        max_range=3.5,
        danger_dist=0.6,
        cooldown_steps=5
    ):
        super().__init__('dagger_lite_collector')

        self.downsample = downsample
        self.rate_hz = rate_hz
        self.max_range = max_range
        self.danger_dist = danger_dist
        self.cooldown_steps = cooldown_steps

        # State variables
        self.scan = None
        self.cmd = None
        self.last_cmd_time = 0.0
        self.cmd_timeout = 0.2  # Seconds before assuming the expert released the joystick
        self.cooldown = 0

        # Thread safety lock for ROS callbacks
        self.lock = threading.Lock()

        # I/O Buffer
        self.data_buffer = []
        self.buffer_size = 50  # Smaller buffer for DAgger since data comes in bursts

        # Subscribers
        self.sub_scan = self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)
        self.sub_cmd = self.create_subscription(Twist, '/cmd_vel', self.cmd_cb, 10)

        # Timer
        self.timer = self.create_timer(1.0 / self.rate_hz, self.record)

        # File I/O setup
        self.out_file = out_file
        os.makedirs(os.path.dirname(out_file) or '.', exist_ok=True)
        self.file = open(self.out_file, 'w', newline='')
        self.writer = csv.writer(self.file)

        self.get_logger().info(
            f"[DAgger-lite] Ready. Collecting ONLY when min_range < {self.danger_dist} m"
        )

    def scan_cb(self, msg: LaserScan):
        with self.lock:
            self.scan = clamp_scan(msg.ranges, self.max_range)

    def cmd_cb(self, msg: Twist):
        with self.lock:
            self.cmd = [msg.linear.x, msg.angular.z]
            self.last_cmd_time = time.time()

    def downsample_scan(self, arr: np.ndarray) -> list:
        """Reduce or pad the LiDAR array to the target input dimension."""
        if len(arr) < self.downsample:
            padded = np.pad(arr, (0, self.downsample - len(arr)), constant_values=self.max_range)
            return padded.tolist()

        idx = np.linspace(0, len(arr) - 1, self.downsample).astype(int)
        return arr[idx].tolist()

    def record(self):
        """Timer callback to check distance and record data if in danger zone."""
        with self.lock:
            if self.scan is None:
                return

            current_scan = self.scan.copy()
            
            # Prevent stale command data
            if self.cmd is None or (time.time() - self.last_cmd_time > self.cmd_timeout):
                current_cmd = [0.0, 0.0]
            else:
                current_cmd = self.cmd.copy()

        # Check safety condition
        min_range = float(np.min(current_scan))

        if self.cooldown > 0:
            self.cooldown -= 1
            return

        # Trigger logic: Only log when close to an obstacle
        if min_range < self.danger_dist:
            scan_ds = self.downsample_scan(current_scan)
            row = [float(x) for x in scan_ds] + [float(current_cmd[0]), float(current_cmd[1])]

            self.data_buffer.append(row)
            self.cooldown = self.cooldown_steps

            self.get_logger().info(
                f"[LOG] Triggered! min_range={min_range:.2f}m | v={current_cmd[0]:.2f}, w={current_cmd[1]:.2f}"
            )

            # Flush to disk if buffer is full
            if len(self.data_buffer) >= self.buffer_size:
                self.flush_buffer()

    def flush_buffer(self):
        """Write stored rows to the CSV file and clear memory."""
        if not self.data_buffer:
            return
        self.writer.writerows(self.data_buffer)
        self.data_buffer.clear()

    def destroy_node(self):
        """Safely clean up resources before shutdown."""
        self.flush_buffer()
        try:
            self.file.close()
        except Exception as e:
            self.get_logger().error(f"Error closing file: {e}")
        super().destroy_node()


# ----------------------------
# MAIN
# ----------------------------

def main(args=None):
    rclpy.init(args=args)

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    parser = argparse.ArgumentParser(description="DAgger-lite Data Collector Node")
    parser.add_argument('--downsample', type=int, default=180, help="Target LiDAR array size")
    parser.add_argument('--rate', type=int, default=20, help="Recording frequency in Hz")
    parser.add_argument('--out', type=str, default=f'logs/dagger_{now_str}.csv', help="Output file path")
    parser.add_argument('--max_range', type=float, default=3.5, help="Maximum LiDAR range")
    parser.add_argument('--danger_dist', type=float, default=0.6, help="Trigger distance threshold")
    parser.add_argument('--cooldown', type=int, default=5, help="Steps to wait between logs")

    parsed, _ = parser.parse_known_args()

    start_time = time.perf_counter()

    node = DAggerCollector(
        downsample=parsed.downsample,
        rate_hz=parsed.rate,
        out_file=parsed.out,
        max_range=parsed.max_range,
        danger_dist=parsed.danger_dist,
        cooldown_steps=parsed.cooldown
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        end_time = time.perf_counter()
        runtime = end_time - start_time

        node.destroy_node()

        # Rename file to include total execution time
        base, ext = os.path.splitext(parsed.out)
        final_name = f"{base}_time_{runtime:.2f}s{ext}"

        try:
            os.rename(parsed.out, final_name)
            print(f"[INFO] Saved DAgger dataset to: {final_name}")
        except Exception as e:
            print(f"[WARN] Failed to rename file: {e}")

        rclpy.shutdown()


if __name__ == '__main__':
    main()
