"""Behavior Cloning Inference Node.

Runs the trained PyTorch PolicyNet in real-time, processes LiDAR scans,
and publishes velocity commands.
"""

import argparse
import os
import sys
import threading

import numpy as np
import rclpy
import torch
from geometry_msgs.msg import Twist
from models.model import PolicyNet
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


def clamp_scan(ranges: list[float], max_range: float = 3.5) -> np.ndarray:
    """Handle NaN/Inf values and clip ranges.

    Args:
        ranges: Raw LiDAR range data.
        max_range: Maximum distance to clip.

    Returns:
        Processed numpy array of ranges.
    """
    arr = np.array(ranges, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=max_range, posinf=max_range, neginf=0.0)
    return np.clip(arr, 0.0, max_range)


class PolicyNode(Node):
    """ROS 2 Node for real-time neural network inference."""

    def __init__(
        self,
        model_path: str,
        downsample: int = 180,
        rate_hz: int = 20,
        max_range: float = 3.5,
    ):
        """Initializes the inference node and loads the model."""
        super().__init__("policy_node")
        self.downsample = downsample
        self.rate = rate_hz
        self.max_range = max_range

        self.scan: np.ndarray | None = None
        self.lock = threading.Lock()

        # UI Throttling
        self.step_counter = 0
        self.log_interval = max(1, int(self.rate / 2))

        # 1. Load PyTorch Model
        if not os.path.exists(model_path):
            self.get_logger().error(f"Model not found: {model_path}")
            sys.exit(1)

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model = PolicyNet(input_dim=self.downsample).to(self.device)

        try:
            state_dict = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model.eval()
            self.get_logger().info(f"Model loaded on {self.device}")
        except Exception as e:
            self.get_logger().error(f"Failed to load weights: {e}")
            sys.exit(1)

        # 2. ROS 2 Communication
        self.sub = self.create_subscription(
            LaserScan, "/scan", self.scan_cb, 10
        )
        self.pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.timer = self.create_timer(1.0 / float(self.rate), self.run_policy)

    def scan_cb(self, msg: LaserScan) -> None:
        """Callback for incoming LiDAR scans."""
        with self.lock:
            self.scan = clamp_scan(msg.ranges, self.max_range)

    def downsample_scan(self, arr: np.ndarray) -> np.ndarray:
        """Reduce or pad the LiDAR array to the target dimension."""
        if len(arr) < self.downsample:
            return np.pad(
                arr,
                (0, self.downsample - len(arr)),
                constant_values=self.max_range,
            )

        idx = np.linspace(0, len(arr) - 1, self.downsample).astype(int)
        return arr[idx]

    def run_policy(self) -> None:
        """Timer loop for processing state and publishing actions."""
        with self.lock:
            if self.scan is None:
                self.get_logger().warn(
                    "Waiting for /scan...", throttle_duration_sec=2.0
                )
                return
            current_scan = self.scan.copy()

        # Preprocessing
        scan_ds = self.downsample_scan(current_scan)
        min_dist = float(np.min(scan_ds))

        # Normalize and convert to tensor
        x_input = np.clip(scan_ds, 0.0, self.max_range) / self.max_range
        x_tensor = (
            torch.tensor(x_input, dtype=torch.float32)
            .unsqueeze(0)
            .to(self.device)
        )

        # Inference
        with torch.no_grad():
            out = self.model(x_tensor).squeeze(0).cpu().numpy()

        # Publish
        msg = Twist()
        msg.linear.x = float(out[0])
        msg.angular.z = float(out[1])
        self.pub.publish(msg)

        # Throttled Logging
        self.step_counter += 1
        if self.step_counter % self.log_interval == 0:
            print(
                f"[RUNNING] min: {min_dist:.2f}m | "
                f"v: {msg.linear.x:+.2f} | w: {msg.angular.z:+.2f}"
            )

    def destroy_node(self) -> None:
        """Stop robot before shutdown."""
        self.pub.publish(Twist())
        self.get_logger().info("Zero velocity sent.")
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Main entry point for inference node."""
    rclpy.init(args=args)

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--downsample", type=int, default=180)
    parser.add_argument("--rate", type=int, default=20)
    parser.add_argument("--max_range", type=float, default=3.5)

    parsed, _ = parser.parse_known_args()

    node = PolicyNode(
        model_path=parsed.model,
        downsample=parsed.downsample,
        rate_hz=parsed.rate,
        max_range=parsed.max_range,
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
