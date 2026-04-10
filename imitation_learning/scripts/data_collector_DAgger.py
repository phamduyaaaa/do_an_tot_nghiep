"""DAgger-lite Data Collector for ROS 2.

Records LiDAR and velocity data ONLY when the robot is near obstacles.
"""

import argparse
import csv
import os
import threading
import time

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


def clamp_scan(ranges: list[float], max_range: float = 3.5) -> np.ndarray:
    """Handle NaN/Inf values and clip ranges.

    Args:
        ranges: List of raw LiDAR ranges.
        max_range: Maximum distance to clip.

    Returns:
        Processed numpy array of ranges.
    """
    arr = np.array(ranges, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=max_range, posinf=max_range, neginf=0.0)
    return np.clip(arr, 0.0, max_range)


class DAggerCollector(Node):
    """ROS 2 Node for collecting expert data in dangerous states."""

    def __init__(
        self,
        downsample: int = 180,
        rate_hz: int = 20,
        out_file: str = "logs/dagger_dataset.csv",
        max_range: float = 3.5,
        danger_dist: float = 0.6,
        cooldown_steps: int = 5,
    ):
        """Initializes the collector node."""
        super().__init__("dagger_lite_collector")

        self.downsample = downsample
        self.rate_hz = rate_hz
        self.max_range = max_range
        self.danger_dist = danger_dist
        self.cooldown_steps = cooldown_steps

        # State variables
        self.scan: np.ndarray | None = None
        self.cmd: list[float] | None = None
        self.last_cmd_time = 0.0
        self.cmd_timeout = 0.2
        self.cooldown = 0

        self.lock = threading.Lock()
        self.data_buffer: list[list[float]] = []
        self.buffer_size = 50

        # ROS Setup
        self.sub_scan = self.create_subscription(
            LaserScan, "/scan", self.scan_cb, 10
        )
        self.sub_cmd = self.create_subscription(
            Twist, "/cmd_vel", self.cmd_cb, 10
        )
        self.timer = self.create_timer(1.0 / self.rate_hz, self.record)

        # File setup
        self.out_file = out_file
        os.makedirs(os.path.dirname(out_file) or ".", exist_ok=True)
        self.file = open(self.out_file, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)

        self.get_logger().info(
            f"[DAgger-lite] Trigger dist: {self.danger_dist}m"
        )

    def scan_cb(self, msg: LaserScan) -> None:
        """Callback for LiDAR scan messages."""
        with self.lock:
            self.scan = clamp_scan(msg.ranges, self.max_range)

    def cmd_cb(self, msg: Twist) -> None:
        """Callback for expert velocity commands."""
        with self.lock:
            self.cmd = [msg.linear.x, msg.angular.z]
            self.last_cmd_time = time.time()

    def downsample_scan(self, arr: np.ndarray) -> list[float]:
        """Downsample LiDAR array to target dimension."""
        if len(arr) < self.downsample:
            padded = np.pad(
                arr,
                (0, self.downsample - len(arr)),
                constant_values=self.max_range,
            )
            return padded.tolist()

        idx = np.linspace(0, len(arr) - 1, self.downsample).astype(int)
        return arr[idx].tolist()

    def record(self) -> None:
        """Timer loop: records data if robot is in danger zone."""
        with self.lock:
            if self.scan is None:
                return
            current_scan = self.scan.copy()
            stale = time.time() - self.last_cmd_time > self.cmd_timeout
            with self.lock:
                if self.scan is None:
                    return
                current_scan = self.scan.copy()
                stale = time.time() - self.last_cmd_time > self.cmd_timeout
                # Fixed: Broken down to stay under 80 characters
                if self.cmd and not stale:
                    cur_cmd = self.cmd.copy()
                else:
                    cur_cmd = [0.0, 0.0]

        min_range = float(np.min(current_scan))
        if self.cooldown > 0:
            self.cooldown -= 1
            return

        if min_range < self.danger_dist:
            scan_ds = self.downsample_scan(current_scan)
            row = [float(x) for x in scan_ds] + [float(c) for c in cur_cmd]
            self.data_buffer.append(row)
            self.cooldown = self.cooldown_steps

            if len(self.data_buffer) >= self.buffer_size:
                self.flush_buffer()

    def flush_buffer(self) -> None:
        """Writes buffer to disk."""
        if self.data_buffer:
            self.writer.writerows(self.data_buffer)
            self.data_buffer.clear()

    def destroy_node(self) -> None:
        """Cleanup resources."""
        self.flush_buffer()
        self.file.close()
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Main entry point."""
    rclpy.init(args=args)
    p = argparse.ArgumentParser()
    p.add_argument("--downsample", type=int, default=180)
    p.add_argument("--rate", type=int, default=20)
    p.add_argument("--out", type=str, default="logs/dagger.csv")
    p.add_argument("--danger_dist", type=float, default=0.6)
    p.add_argument("--cooldown", type=int, default=5)
    parsed, _ = p.parse_known_args()

    node = DAggerCollector(
        downsample=parsed.downsample,
        rate_hz=parsed.rate,
        out_file=parsed.out,
        danger_dist=parsed.danger_dist,
        cooldown_steps=parsed.cooldown,
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
