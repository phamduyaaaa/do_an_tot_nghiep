#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Quaternion, TransformStamped
from tf_transformations import quaternion_from_euler
from tf2_ros import TransformBroadcaster
import math


class EncoderIMUToOdomNode(Node):
    def __init__(self):
        super().__init__('odom2')

        # Parameters
        self.declare_parameter('r_banh', 0.1)
        self.declare_parameter('khoang_cach_banh', 0.5)
        self.declare_parameter('left_topic', 'wheel_data_left')
        self.declare_parameter('right_topic', 'wheel_data_right')
        self.declare_parameter('imu_topic', 'imu/data')
        self.declare_parameter('odom_topic', 'odom')

        # Get parameter values
        self.r_banh = self.get_parameter('r_banh').get_parameter_value().double_value
        self.khoang_cach_banh = self.get_parameter('khoang_cach_banh').get_parameter_value().double_value
        self.left_topic = self.get_parameter('left_topic').get_parameter_value().string_value
        self.right_topic = self.get_parameter('right_topic').get_parameter_value().string_value
        self.imu_topic = self.get_parameter('imu_topic').get_parameter_value().string_value
        self.odom_topic = self.get_parameter('odom_topic').get_parameter_value().string_value

        # State variables
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_time = self.get_clock().now()

        # Wheel and IMU data placeholders
        self.left_rpm = 0.0
        self.right_rpm = 0.0
        self.yaw_rate = 0.0  # Angular velocity (yaw rate) from IMU

        # Subscribers
        self.create_subscription(Float64MultiArray, self.left_topic, self.left_wheel_callback, 10)
        self.create_subscription(Float64MultiArray, self.right_topic, self.right_wheel_callback, 10)
        self.create_subscription(Imu, self.imu_topic, self.imu_callback, 10)

        # Publisher
        self.odom_pub = self.create_publisher(Odometry, self.odom_topic, 10)

        # Transform Broadcaster
        self.tf_broadcaster = TransformBroadcaster(self)

        self.get_logger().info("EncoderIMUToOdomNode started")

    def left_wheel_callback(self, msg):
        if len(msg.data) != 2:
            self.get_logger().warn("Left wheel data must have exactly two values.")
            return
        self.left_rpm = (msg.data[0] + msg.data[1]) / 2.0
        self.update_odom()

    def right_wheel_callback(self, msg):
        if len(msg.data) != 2:
            self.get_logger().warn("Right wheel data must have exactly two values.")
            return
        self.right_rpm = (msg.data[0] + msg.data[1]) / 2.0
        self.update_odom()

    def imu_callback(self, msg):
        # Lấy vận tốc góc (yaw rate) từ IMU
        self.yaw_rate = msg.angular_velocity.z

    def update_odom(self):
        # Chuyển đổi RPM thành vận tốc (m/s)
        left_velocity = (self.left_rpm * 2 * math.pi * self.r_banh) / 60.0
        right_velocity = (self.right_rpm * 2 * math.pi * self.r_banh) / 60.0

        # Tính toán vận tốc tuyến tính và góc quay
        linear_velocity = (left_velocity + right_velocity) / 2.0
        angular_velocity = self.yaw_rate  # Sử dụng yaw rate từ IMU thay vì từ encoder

        # Tính toán thời gian delta
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9
        self.last_time = current_time

        # Cập nhật vị trí (x, y) và góc quay (theta)
        delta_x = linear_velocity * math.cos(self.theta) * dt
        delta_y = linear_velocity * math.sin(self.theta) * dt
        delta_theta = angular_velocity * dt

        self.x += delta_x
        self.y += delta_y
        self.theta += delta_theta

        # Đảm bảo theta luôn nằm trong khoảng [-pi, pi]
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))

        # Tạo quaternion từ góc theta
        q = quaternion_from_euler(0, 0, self.theta)

        # Tạo message Odometry
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_footprint'

        # Điền thông tin vị trí
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation = Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])

        # Điền thông tin vận tốc
        odom.twist.twist.linear.x = linear_velocity
        odom.twist.twist.linear.y = 0.0
        odom.twist.twist.angular.z = angular_velocity

        # Publish Odometry
        self.odom_pub.publish(odom)

        # Broadcast TF transform
        transform = TransformStamped()
        transform.header.stamp = current_time.to_msg()
        transform.header.frame_id = 'odom'
        transform.child_frame_id = 'base_footprint'
        transform.transform.translation.x = self.x
        transform.transform.translation.y = self.y
        transform.transform.translation.z = 0.0
        transform.transform.rotation = Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])

        self.tf_broadcaster.sendTransform(transform)


def main(args=None):
    rclpy.init(args=args)
    node = EncoderIMUToOdomNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

