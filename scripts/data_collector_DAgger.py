import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
import numpy as np
import csv
import os
import argparse


def clamp_scan(ranges, max_range=3.5):
    arr = np.array(ranges, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=max_range, posinf=max_range, neginf=0.0)
    arr = np.clip(arr, 0.0, max_range)
    return arr


class DataCollector(Node):
    def __init__(
        self,
        downsample=180,
        rate_hz=20,
        out_file='dataset.csv',
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

        self.scan = None
        self.cmd = None
        self.cooldown = 0

        # Subscribers
        self.sub_scan = self.create_subscription(
            LaserScan, '/scan', self.scan_cb, 10
        )
        self.sub_cmd = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_cb, 10
        )

        # Timer
        self.timer = self.create_timer(
            1.0 / float(self.rate_hz),
            self.record
        )

        # Output file
        self.out_file = out_file
        os.makedirs(os.path.dirname(out_file) or '.', exist_ok=True)
        self.file = open(self.out_file, 'w', newline='')
        self.writer = csv.writer(self.file)

        self.get_logger().info(
            f"[DAgger-lite] Collecting ONLY when min_range < {self.danger_dist} m"
        )

    # ----------------------------
    # Callbacks
    # ----------------------------

    def scan_cb(self, msg):
        self.scan = clamp_scan(msg.ranges, self.max_range)

    def cmd_cb(self, msg):
        self.cmd = [msg.linear.x, msg.angular.z]

    # ----------------------------
    # Downsample LIDAR
    # ----------------------------

    def downsample_scan(self, arr):
        if len(arr) < self.downsample:
            padded = np.pad(
                arr,
                (0, self.downsample - len(arr)),
                constant_values=self.max_range
            )
            return padded.tolist()

        idx = np.linspace(0, len(arr) - 1, self.downsample).astype(int)
        return arr[idx].tolist()

    # ----------------------------
    # DAgger-lite record logic
    # ----------------------------

    def record(self):
        if self.scan is None or self.cmd is None:
            return

        min_range = float(np.min(self.scan))

        # Cooldown để tránh log liên tục
        if self.cooldown > 0:
            self.cooldown -= 1
            return

        # Trigger: chỉ log khi nguy hiểm
        if min_range < self.danger_dist:
            scan_ds = self.downsample_scan(self.scan)

            row = [float(x) for x in scan_ds] + \
                  [float(self.cmd[0]), float(self.cmd[1])]

            self.writer.writerow(row)
            self.cooldown = self.cooldown_steps

            self.get_logger().info(
                f"[LOG] min_range={min_range:.2f} m | v={self.cmd[0]:.2f}, w={self.cmd[1]:.2f}"
            )

    # ----------------------------
    # Clean up
    # ----------------------------

    def destroy_node(self):
        try:
            self.file.close()
        except Exception:
            pass
        super().destroy_node()


# ----------------------------
# MAIN
# ----------------------------

def main(args=None):
    rclpy.init(args=args)

    parser = argparse.ArgumentParser()
    parser.add_argument('--downsample', type=int, default=180)
    parser.add_argument('--rate', type=int, default=20)
    parser.add_argument('--out', type=str, default='dataset.csv')
    parser.add_argument('--max_range', type=float, default=3.5)
    parser.add_argument('--danger_dist', type=float, default=0.6)
    parser.add_argument('--cooldown', type=int, default=5)

    parsed, _ = parser.parse_known_args()

    node = DataCollector(
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
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

