import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
import numpy as np
import argparse
import torch
from model import PolicyNet


def clamp_scan(ranges, max_range=3.5):
    arr = np.array(ranges, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=max_range, posinf=max_range, neginf=0.0)
    arr = np.clip(arr, 0.0, max_range)
    return arr


class PolicyNode(Node):
    def __init__(self, model_path, downsample=180, rate_hz=20, max_range=3.5):
        super().__init__('policy_node')
        self.downsample = downsample
        self.rate = rate_hz
        self.max_range = max_range

        self.scan = None

        # Subscriber /scan
        self.sub = self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)

        # Publisher /cmd_vel
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Timer để chạy policy
        self.timer = self.create_timer(1.0 / float(self.rate), self.run_policy)

        # Load model
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = PolicyNet(input_dim=self.downsample)
        self.model.load_state_dict(torch.load(model_path, map_location=device))
        self.model.eval()
        self.get_logger().info(f'Loaded model from {model_path}')

    def scan_cb(self, msg):
        self.scan = clamp_scan(msg.ranges, self.max_range)

    def downsample_scan(self, arr):
        idx = np.linspace(0, len(arr) - 1, self.downsample).astype(int)
        return arr[idx]

    def run_policy(self):
        if self.scan is None:
            return

        scan_ds = self.downsample_scan(self.scan)
        x = np.clip(scan_ds, 0.0, self.max_range) / self.max_range
        x = torch.tensor(x, dtype=torch.float32).unsqueeze(0)  # batch=1
        

        with torch.no_grad():
            out = self.model(x).squeeze(0).numpy()

        msg = Twist()
        msg.linear.x = float(out[0])
        msg.angular.z = float(out[1])
        print(f"LINEAR X: {msg.linear.x} | ANGULAR Z: {msg.angular.z}")
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, required=True, help='Path to trained bc_model.pth')
    parser.add_argument('--downsample', type=int, default=180)
    parser.add_argument('--rate', type=int, default=20)
    parser.add_argument('--max_range', type=float, default=3.5)
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

