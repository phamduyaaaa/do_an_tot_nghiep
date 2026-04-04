#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64MultiArray
import math

class KinematicNode(Node):
    def __init__(self):
        super().__init__('kinematic')

        self.declare_parameter('khoang_cach_banh', 0.47)
        self.declare_parameter('r_banh', 0.1)
        self.declare_parameter('output_topic', 'kine_to_ZLA8015D')
        self.declare_parameter('pi', math.pi)
        self.declare_parameter('input_topic', 'cmd_vel')

        self.khoang_cach_banh = self.get_parameter('khoang_cach_banh').get_parameter_value().double_value
        self.r_banh = self.get_parameter('r_banh').get_parameter_value().double_value
        self.pi = self.get_parameter('pi').get_parameter_value().double_value
        self.input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        self.output_topic = self.get_parameter('output_topic').get_parameter_value().string_value

        self.pub = self.create_publisher(Float64MultiArray, self.output_topic, 5)
        self.sub = self.create_subscription(
            Twist,
            self.input_topic,
            self.dong_hoc,
            10
        )

        self.msg = Float64MultiArray()
        self.get_logger().info(f"Kinematic Node Started")

    def gioi_han(self, a):
        if a >= 300:
            a = 300
        elif a <= -300 and a != 0:
            a = -300
        return a

    def dong_hoc(self, gmsg):
        v_thang_x = gmsg.linear.x
        v_quay_z = gmsg.angular.z

        omega_l = ((v_thang_x - (v_quay_z * (self.khoang_cach_banh / 2))) / self.r_banh) * (60 / (2 * self.pi))
        omega_r = ((v_thang_x + (v_quay_z * (self.khoang_cach_banh / 2))) / self.r_banh) * (60 / (2 * self.pi))

        omega_l = self.gioi_han(omega_l)
        omega_r = self.gioi_han(omega_r)

        self.msg.data = [omega_l, omega_r]

        # self.get_logger().info(f"Vận tốc thẳng đặt là: {v_thang_x:.2f}")
        # self.get_logger().info(f"Vận tốc góc đặt là: {v_quay_z:.2f}")
        # self.get_logger().info(f"RPM trái đặt là: {omega_l:.3f}")
        # self.get_logger().info(f"RPM phải đặt là: {omega_r:.3f}")

        self.pub.publish(self.msg)

def main(args=None):    
    
    rclpy.init(args=args)

    node = KinematicNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

