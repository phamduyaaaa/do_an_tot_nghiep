"""
================================================================================
Behavior Cloning Inference Node

* Purpose: Runs the trained PyTorch PolicyNet in real-time. Subscribes to LiDAR, 
           processes the state, queries the neural network, and publishes velocity 
           commands. Optimized for Streamlit dashboard monitoring.
* Inputs:  - /scan (sensor_msgs/LaserScan)
* Outputs: - /cmd_vel (geometry_msgs/Twist)
* Args:    - --model (str): Path to the trained PyTorch checkpoint (.pth)
           - --downsample (int): Target LiDAR array size (must match training)
           - --rate (int): Control loop frequency in Hz (default: 20)
           - --max_range (float): Maximum LiDAR range (default: 3.5)
* Usage:   python scripts/inference.py --model checkpoints/bc_model.pth
================================================================================
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
import numpy as np
import argparse
import torch
import os
import sys
import threading
from models.model import PolicyNet


def clamp_scan(ranges: list, max_range: float = 3.5) -> np.ndarray:
    """Handle NaN/Inf values and clip ranges using fast numpy vectorization."""
    arr = np.array(ranges, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=max_range, posinf=max_range, neginf=0.0)
    return np.clip(arr, 0.0, max_range)


class PolicyNode(Node):
    def __init__(self, model_path, downsample=180, rate_hz=20, max_range=3.5):
        super().__init__('policy_node')
        self.downsample = downsample
        self.rate = rate_hz
        self.max_range = max_range

        self.scan = None
        self.lock = threading.Lock()

        # For Streamlit Log Throttling (avoid freezing the web UI)
        self.step_counter = 0
        self.log_interval = max(1, int(self.rate / 2))  # Print ~2 times per second

        # 1. Load PyTorch Model
        if not os.path.exists(model_path):
            self.get_logger().error(f"Model file not found: {model_path}")
            sys.exit(1)

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = PolicyNet(input_dim=self.downsample).to(self.device)
        
        try:
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            self.model.eval()
            self.get_logger().info(f"[INFO] Loaded model successfully on {self.device}")
        except Exception as e:
            self.get_logger().error(f"Failed to load model weights: {e}")
            sys.exit(1)

        # 2. ROS 2 Communication Setup
        self.sub = self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(1.0 / float(self.rate), self.run_policy)

    def scan_cb(self, msg: LaserScan):
        with self.lock:
            self.scan = clamp_scan(msg.ranges, self.max_range)

    def downsample_scan(self, arr: np.ndarray) -> np.ndarray:
        """Reduce or pad the LiDAR array to the target input dimension."""
        if len(arr) < self.downsample:
            # Pad missing values with max_range (free space)
            padded = np.pad(arr, (0, self.downsample - len(arr)), constant_values=self.max_range)
            return padded

        idx = np.linspace(0, len(arr) - 1, self.downsample).astype(int)
        return arr[idx]

    def run_policy(self):
        with self.lock:
            if self.scan is None:
                self.get_logger().warn("Waiting for /scan data...", throttle_duration_sec=2.0)
                return
            current_scan = self.scan.copy()

        # Data Preprocessing
        scan_ds = self.downsample_scan(current_scan)
        min_dist = float(np.min(scan_ds))
        
        # Normalize input to [0, 1]
        x_input = np.clip(scan_ds, 0.0, self.max_range) / self.max_range
        
        # Convert to tensor and send to correct device (Fixes CPU/CUDA mismatch)
        x_tensor = torch.tensor(x_input, dtype=torch.float32).unsqueeze(0).to(self.device)

        # Neural Network Inference
        with torch.no_grad():
            out = self.model(x_tensor).squeeze(0).cpu().numpy()

        # Publish Command
        msg = Twist()
        msg.linear.x = float(out[0])
        msg.angular.z = float(out[1])
        self.pub.publish(msg)

        # UI-Friendly Logging (Throttled)
        self.step_counter += 1
        if self.step_counter % self.log_interval == 0:
            print(f"[RUNNING] min_dist: {min_dist:.2f}m | v: {msg.linear.x:+.2f} m/s | w: {msg.angular.z:+.2f} rad/s")

    def destroy_node(self):
        """Send stop command before shutting down to prevent runaway robot."""
        stop_msg = Twist()
        self.pub.publish(stop_msg)
        self.get_logger().info("Sent zero velocity stop command.")
        super().destroy_node()


# ----------------------------
# MAIN
# ----------------------------

def main(args=None):
    rclpy.init(args=args)
    
    parser = argparse.ArgumentParser(description="Run BC Inference Node")
    parser.add_argument('--model', type=str, required=True, help='Path to trained bc_model.pth')
    parser.add_argument('--downsample', type=int, default=180, help='LiDAR array size')
    parser.add_argument('--rate', type=int, default=20, help='Control frequency (Hz)')
    parser.add_argument('--max_range', type=float, default=3.5, help='Max LiDAR range')
    
    parsed, _ = parser.parse_known_args()

    node = PolicyNode(
        model_path=parsed.model,
        downsample=parsed.downsample,
        rate_hz=parsed.rate,
        max_range=parsed.max_range
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
