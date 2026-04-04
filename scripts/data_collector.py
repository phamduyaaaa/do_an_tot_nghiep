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


def clamp_scan(ranges, max_range=3.5):
    arr = np.array(ranges, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=max_range, posinf=max_range, neginf=0.0)
    arr = np.clip(arr, 0.0, max_range)
    return arr


class DataCollector(Node):
    def __init__(self, downsample=180, rate_hz=20, out_file='dataset.csv', max_range=3.5):
        super().__init__('il_data_collector')

        self.downsample = downsample
        self.rate_hz = rate_hz
        self.max_range = max_range

        self.scan = None
        self.cmd = None

        # Subscribers
        self.sub_scan = self.create_subscription(
            LaserScan, '/scan', self.scan_cb, 10
        )
        self.sub_cmd = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_cb, 10
        )

        # Timer
        self.timer = self.create_timer(1.0 / float(self.rate_hz), self.record)

        # Output file
        self.out_file = out_file
        os.makedirs(os.path.dirname(out_file) or '.', exist_ok=True)
        self.file = open(self.out_file, 'w', newline='')
        self.writer = csv.writer(self.file)

        self.get_logger().info(f"[IL] DataCollector started, output: {self.out_file}")

    def scan_cb(self, msg):
        self.scan = clamp_scan(msg.ranges, self.max_range)

    def cmd_cb(self, msg):
        self.cmd = [msg.linear.x, msg.angular.z]

    def downsample_scan(self, arr):
        if len(arr) < self.downsample:
            padded = np.pad(arr, (0, self.downsample - len(arr)), constant_values=0.0)
            return padded.tolist()

        idx = np.linspace(0, len(arr) - 1, self.downsample).astype(int)
        return arr[idx].tolist()

    def record(self):
        if self.scan is None or self.cmd is None:
            return

        scan_ds = self.downsample_scan(self.scan)

        row = [float(x) for x in scan_ds] + \
              [float(self.cmd[0]), float(self.cmd[1])]

        self.writer.writerow(row)

    def close_file(self):
        try:
            self.file.close()
        except Exception:
            pass

    def destroy_node(self):
        self.close_file()
        super().destroy_node()


# ----------------------------
# MAIN
# ----------------------------

def main(args=None):
    rclpy.init(args=args)

    # ===== Timestamp lúc start =====
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    parser = argparse.ArgumentParser()
    parser.add_argument('--downsample', type=int, default=180)
    parser.add_argument('--rate', type=int, default=20)
    parser.add_argument('--out', type=str, default=f'dataset_{now_str}.csv')
    parser.add_argument('--max_range', type=float, default=3.5)
    parsed, _ = parser.parse_known_args()

    # ===== Timing start =====
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
        # ===== Timing end =====
        end_time = time.perf_counter()
        runtime = end_time - start_time

        node.close_file()

        # ===== Rename =====
        base, ext = os.path.splitext(parsed.out)
        final_name = f"{base}_time_{runtime:.2f}s{ext}"

        try:
            os.rename(parsed.out, final_name)
            print(f"[INFO] Saved file: {final_name}")
        except Exception as e:
            print(f"[WARN] Rename failed: {e}")

        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
