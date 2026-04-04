"""
================================================================================
Imitation Learning Data Collector

* Purpose: ROS 2 node that records expert demonstrations by subscribing to 
           LiDAR scans and velocity commands, saving them synchronously to a CSV.
           Features thread safety, I/O buffering, and stale data prevention.
* Inputs:  - /scan (sensor_msgs/LaserScan)
           - /cmd_vel (geometry_msgs/Twist)
* Outputs: - CSV file: [scan_1, scan_2, ..., scan_N, linear_x, angular_z]
* Args:    - --downsample (int): Target size for LiDAR array (default: 180)
           - --rate (int): Data recording frequency in Hz (default: 20)
           - --out (str): Path to save the output CSV file
           - --max_range (float): Maximum LiDAR range in meters (default: 3.5)
* Usage:   python3 data_collector.py --out data/dataset.csv --rate 20
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
from datetime import datetime
import time
import threading


def clamp_scan(ranges: list, max_range: float = 3.5) -> np.ndarray:
    """Handle NaN/Inf values and clip ranges using fast numpy vectorization."""
    arr = np.array(ranges, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=max_range, posinf=max_range, neginf=0.0)
    return np.clip(arr, 0.0, max_range)


class DataCollector(Node):
    def __init__(self, downsample=180, rate_hz=20, out_file='data/dataset.csv', max_range=3.5):
        super().__init__('il_data_collector')

        self.downsample = downsample
        self.rate_hz = rate_hz
        self.max_range = max_range

        # State variables
        self.scan = None
        self.cmd = None
        self.last_cmd_time = 0.0
        self.cmd_timeout = 0.2  # Seconds before assuming the robot has stopped

        # Thread safety lock for ROS callbacks
        self.lock = threading.Lock()

        # I/O Buffer to prevent disk blocking during high-frequency loops
        self.data_buffer = []
        self.buffer_size = 100

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

        self.get_logger().info(f"[IL] DataCollector started, output: {self.out_file}")

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
            # Pad missing values with max_range (free space) instead of 0.0 (obstacles)
            padded = np.pad(arr, (0, self.downsample - len(arr)), constant_values=self.max_range)
            return padded.tolist()

        idx = np.linspace(0, len(arr) - 1, self.downsample).astype(int)
        return arr[idx].tolist()

    def record(self):
        """Timer callback to record synchronized state-action pairs."""
        with self.lock:
            if self.scan is None:
                return
            
            current_scan = self.scan.copy()
            
            # Prevent stale command data if joystick is released
            if self.cmd is None or (time.time() - self.last_cmd_time > self.cmd_timeout):
                current_cmd = [0.0, 0.0]  # Default to zero velocity
            else:
                current_cmd = self.cmd.copy()

        # Process data
        scan_ds = self.downsample_scan(current_scan)
        row = [float(x) for x in scan_ds] + [float(current_cmd[0]), float(current_cmd[1])]

        # Append to memory buffer
        self.data_buffer.append(row)

        # Flush to disk only when buffer is full
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
        self.flush_buffer()  # Ensure remaining data is saved
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

    # Generate timestamp for default filename
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    parser = argparse.ArgumentParser(description="IL Data Collector Node")
    parser.add_argument('--downsample', type=int, default=180, help="Target LiDAR array size")
    parser.add_argument('--rate', type=int, default=20, help="Recording frequency in Hz")
    parser.add_argument('--out', type=str, default=f'logs/dataset_{now_str}.csv', help="Output file path")
    parser.add_argument('--max_range', type=float, default=3.5, help="Maximum LiDAR range")
    
    parsed, _ = parser.parse_known_args()

    # Performance timing
    start_time = time.perf_counter()

    node = DataCollector(
        downsample=parsed.downsample,
        rate_hz=parsed.rate,
        out_file=parsed.out,
        max_range=parsed.max_range
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
            print(f"[INFO] Saved dataset to: {final_name}")
        except Exception as e:
            print(f"[WARN] Failed to rename file: {e}")

        rclpy.shutdown()


if __name__ == '__main__':
    main()
