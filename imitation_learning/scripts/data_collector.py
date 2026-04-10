"""Imitation Learning Data Collector.

Records expert demonstrations by subscribing to LiDAR scans and
velocity commands, saving them synchronously to a CSV file.
"""

import argparse
import csv
import os
import threading
import time
from datetime import datetime

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


def clamp_scan(ranges: list[float], max_range: float = 3.5) -> np.ndarray:
    """Handle NaN/Inf values and clip ranges using fast numpy vectorization.

    Args:
        ranges: Raw LiDAR range data.
        max_range: Maximum distance to clip.

    Returns:
        Processed numpy array of ranges.
    """
    arr = np.array(ranges, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=max_range, posinf=max_range, neginf=0.0)
    return np.clip(arr, 0.0, max_range)


class DataCollector(Node):
    """ROS 2 Node for collecting synchronized state-action pairs."""

    def __init__(
        self,
        downsample: int = 180,
        rate_hz: int = 20,
        out_file: str = "data/dataset.csv",
        max_range: float = 3.5,
    ):
        """Initializes the DataCollector node."""
        super().__init__("il_data_collector")

        self.downsample = downsample
        self.rate_hz = rate_hz
        self.max_range = max_range

        # State variables
        self.scan: np.ndarray | None = None
        self.cmd: list[float] | None = None
        self.last_cmd_time = 0.0
        self.cmd_timeout = 0.2

        # Thread safety and buffering
        self.lock = threading.Lock()
        self.data_buffer: list[list[float]] = []
        self.buffer_size = 100

        # Subscribers
        self.sub_scan = self.create_subscription(
            LaserScan, "/scan", self.scan_cb, 10
        )
        self.sub_cmd = self.create_subscription(
            Twist, "/cmd_vel", self.cmd_cb, 10
        )

        # Timer
        self.timer = self.create_timer(1.0 / self.rate_hz, self.record)

        # File setup
        self.out_file = out_file
        os.makedirs(os.path.dirname(out_file) or ".", exist_ok=True)
        self.file = open(self.out_file, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)

        self.get_logger().info(f"[IL] Collector started: {self.out_file}")

    def scan_cb(self, msg: LaserScan) -> None:
        """Processes incoming LiDAR scans."""
        with self.lock:
            self.scan = clamp_scan(msg.ranges, self.max_range)

    def cmd_cb(self, msg: Twist) -> None:
        """Processes incoming velocity commands."""
        with self.lock:
            self.cmd = [msg.linear.x, msg.angular.z]
            self.last_cmd_time = time.time()

    def downsample_scan(self, arr: np.ndarray) -> list[float]:
        """Downsample or pad the LiDAR array to the target dimension."""
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
        """Timer loop: captures synchronized data at specific frequency."""
        with self.lock:
            if self.scan is None:
                return

            current_scan = self.scan.copy()
            stale = (time.time() - self.last_cmd_time) > self.cmd_timeout

            if self.cmd and not stale:
                current_cmd = self.cmd.copy()
            else:
                current_cmd = [0.0, 0.0]

        # Process and store
        scan_ds = self.downsample_scan(current_scan)
        row = [float(x) for x in scan_ds] + [
            float(current_cmd[0]),
            float(current_cmd[1]),
        ]

        self.data_buffer.append(row)

        if len(self.data_buffer) >= self.buffer_size:
            self.flush_buffer()

    def flush_buffer(self) -> None:
        """Writes buffer content to disk."""
        if self.data_buffer:
            self.writer.writerows(self.data_buffer)
            self.data_buffer.clear()

    def destroy_node(self) -> None:
        """Closes resources and saves remaining data."""
        self.flush_buffer()
        try:
            self.file.close()
        except OSError as e:
            self.get_logger().error(f"Error closing file: {e}")
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Entry point for the data collection node."""
    rclpy.init(args=args)

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser()
    parser.add_argument("--downsample", type=int, default=180)
    parser.add_argument("--rate", type=int, default=20)
    parser.add_argument("--out", type=str, default=f"logs/dataset_{now_str}.csv")  # noqa: E501
    parser.add_argument("--max_range", type=float, default=3.5)

    parsed, _ = parser.parse_known_args()
    start_time = time.perf_counter()

    node = DataCollector(
        downsample=parsed.downsample,
        rate_hz=parsed.rate,
        out_file=parsed.out,
        max_range=parsed.max_range,
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        runtime = time.perf_counter() - start_time
        node.destroy_node()

        # Finalize filename with runtime
        base, ext = os.path.splitext(parsed.out)
        final_name = f"{base}_time_{runtime:.2f}s{ext}"
        try:
            os.rename(parsed.out, final_name)
            print(f"[INFO] Saved dataset: {final_name}")
        except OSError as e:
            print(f"[WARN] Failed rename: {e}")

        rclpy.shutdown()


if __name__ == "__main__":
    main()
