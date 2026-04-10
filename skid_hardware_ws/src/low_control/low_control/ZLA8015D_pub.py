# #!/usr/bin/env python3
# import rclpy
# from rclpy.node import Node
# import numpy as np
# from std_msgs.msg import Float64MultiArray
# from pymodbus.client.sync import ModbusSerialClient as ModbusClient

# modbus_client = ModbusClient(method='rtu', port='/dev/ttyUSB0', baudrate=115200, timeout=3)
# modbus_client.connect()

# SLAVE_ID_L = 1
# SLAVE_ID_R = 2

# OPR_MODE = 0x200D
# SY_OR_ASSY = 0x200F
# CONTROL_REG = 0x200E
# FRONT_CMD_RPM = 0x2088
# BACK_CMD_RPM = 0x2089
# FRONT_FB_RPM = 0x20AB
# BACK_FB_RPM = 0x20AC
# ENABLE = 0x08

# def chuyen_doi(value):
#     value = int(value)
#     low_byte = (value & 0x00FF)
#     high_byte = (value >> 8) & 0x00FF
#     return (high_byte << 8) | low_byte

# def set_velocity_mode(slave_id):
#     modbus_client.write_register(OPR_MODE, 3, unit=slave_id)
#     modbus_client.write_register(SY_OR_ASSY, 1, unit=slave_id)
#     modbus_client.write_register(CONTROL_REG, ENABLE, unit=slave_id)

# def set_motor_speed(slave_id, left_speed, right_speed):
#     modbus_client.write_register(FRONT_CMD_RPM, left_speed, unit=slave_id)
#     modbus_client.write_register(BACK_CMD_RPM, right_speed, unit=slave_id)

# def read_motor_speed(slave_id):
#     try:
#         rpm_front = modbus_client.read_holding_registers(FRONT_FB_RPM, 1, unit=slave_id)
#         rpm_back = modbus_client.read_holding_registers(BACK_FB_RPM, 1, unit=slave_id)
#         fb_front_rpm = np.array([rpm_front.registers[0]]).astype(np.int16)[0] / 10.0
#         fb_back_rpm = np.array([rpm_back.registers[0]]).astype(np.int16)[0] / 10.0
#         return fb_front_rpm, fb_back_rpm
#     except Exception as e:
#         print(f"Lỗi khi đọc tốc độ từ driver {slave_id}: {e}")
#         return None, None

# class ZLA8015DDriverNode(Node):
#     def __init__(self):
#         super().__init__('zla8015d_driver_node')

#         self.declare_parameter('input_topic', 'kine_to_ZLA8015D')
#         self.declare_parameter('output_topic', 'wheel_data')
#         self.declare_parameter('output_topic_left', 'wheel_data_left')
#         self.declare_parameter('output_topic_right', 'wheel_data_right')

#         input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
#         output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
#         output_topic_left = self.get_parameter('output_topic_left').get_parameter_value().string_value
#         output_topic_right = self.get_parameter('output_topic_right').get_parameter_value().string_value

#         self.pub = self.create_publisher(Float64MultiArray, output_topic, 5)
#         self.pub_left = self.create_publisher(Float64MultiArray, output_topic_left, 5)
#         self.pub_right = self.create_publisher(Float64MultiArray, output_topic_right, 5)

#         self.create_subscription(Float64MultiArray, input_topic, self.wheel_speed_callback, 5)

#         self.received_kine_data = False
#         self.timer = self.create_timer(0.5, self.check_kine_timeout)

#         set_velocity_mode(SLAVE_ID_L)
#         set_velocity_mode(SLAVE_ID_R)

#     def wheel_speed_callback(self, msg):
#         """ Callback khi nhận được dữ liệu từ topic kine_to_ZLA8015D """
#         if len(msg.data) == 2:
#             left_speed = msg.data[0]
#             right_speed = msg.data[1]

#             self.received_kine_data = True

#             set_motor_speed(SLAVE_ID_L, chuyen_doi(left_speed), chuyen_doi(left_speed))
#             set_motor_speed(SLAVE_ID_R, chuyen_doi(-right_speed), chuyen_doi(-right_speed))

#             left_speed_front, left_speed_back = read_motor_speed(SLAVE_ID_L)
#             right_speed_front, right_speed_back = read_motor_speed(SLAVE_ID_R)

#             stand_data = Float64MultiArray(data=[left_speed, right_speed])
#             feedback_left = Float64MultiArray(data=[left_speed_front, left_speed_back])
#             feedback_right = Float64MultiArray(data=[-right_speed_front, -right_speed_back])

#             self.pub.publish(stand_data)
#             self.pub_left.publish(feedback_left)
#             self.pub_right.publish(feedback_right)

#     def check_kine_timeout(self):
#         """ Nếu không nhận được dữ liệu từ topic kine_to_ZLA8015D, dừng robot """
#         if not self.received_kine_data:
#             print("Không nhận được dữ liệu từ kine_to_ZLA8015D, dừng robot!")

#             set_motor_speed(SLAVE_ID_L, 0, 0)
#             set_motor_speed(SLAVE_ID_R, 0, 0)

#             stand_data = Float64MultiArray(data=[0.0, 0.0])
#             feedback_left = Float64MultiArray(data=[0.0, 0.0])
#             feedback_right = Float64MultiArray(data=[0.0, 0.0])

#             self.pub.publish(stand_data)
#             self.pub_left.publish(feedback_left)
#             self.pub_right.publish(feedback_right)

#         self.received_kine_data = False

# def main(args=None):
#     rclpy.init(args=args)
#     node = ZLA8015DDriverNode()

#     try:
#         rclpy.spin(node)
#     except KeyboardInterrupt:
#         pass

#     modbus_client.close()
#     node.destroy_node()
#     rclpy.shutdown()

# if __name__ == '__main__':
#     main()

import numpy as np

#!/usr/bin/env python3
import rclpy
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

modbus_client = ModbusClient(method='rtu', port='/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A5069RR4-if00-port0', baudrate=115200, timeout=3)
modbus_client.connect()

SLAVE_ID_L = 1
SLAVE_ID_R = 2

OPR_MODE = 0x200D
SY_OR_ASSY = 0x200F
CONTROL_REG = 0x200E
FRONT_CMD_RPM = 0x2088
BACK_CMD_RPM = 0x2089
FRONT_FB_RPM = 0x20AB
BACK_FB_RPM = 0x20AC
ENABLE = 0x08

def chuyen_doi(value):
    value = int(value)
    low_byte = (value & 0x00FF)
    high_byte = (value >> 8) & 0x00FF
    return (high_byte << 8) | low_byte

def set_velocity_mode(slave_id):
    modbus_client.write_register(OPR_MODE, 3, unit=slave_id)
    modbus_client.write_register(SY_OR_ASSY, 1, unit=slave_id)
    modbus_client.write_register(CONTROL_REG, ENABLE, unit=slave_id)

def set_motor_speed(slave_id, left_speed, right_speed):
    modbus_client.write_register(FRONT_CMD_RPM, left_speed, unit=slave_id)
    modbus_client.write_register(BACK_CMD_RPM, right_speed, unit=slave_id)

def read_motor_speed(slave_id):
    try:
        rpm_front = modbus_client.read_holding_registers(FRONT_FB_RPM, 1, unit=slave_id)
        rpm_back = modbus_client.read_holding_registers(BACK_FB_RPM, 1, unit=slave_id)

        if rpm_front is None or rpm_back is None or not hasattr(rpm_front, 'registers') or not hasattr(rpm_back, 'registers'):
            print(f"Lỗi: Không nhận được phản hồi từ driver {slave_id}")
            return None, None

        fb_front_rpm = np.array([rpm_front.registers[0]]).astype(np.int16)[0] / 10.0
        fb_back_rpm = np.array([rpm_back.registers[0]]).astype(np.int16)[0] / 10.0
        return fb_front_rpm, fb_back_rpm
    except Exception as e:
        print(f"Lỗi khi đọc tốc độ từ driver {slave_id}: {e}")
        return None, None

class ZLA8015DDriverNode(Node):
    def __init__(self):
        super().__init__('zla8015d_driver_node')

        self.declare_parameter('input_topic', 'kine_to_ZLA8015D')
        self.declare_parameter('output_topic', 'wheel_data')
        self.declare_parameter('output_topic_left', 'wheel_data_left')
        self.declare_parameter('output_topic_right', 'wheel_data_right')

        input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        output_topic_left = self.get_parameter('output_topic_left').get_parameter_value().string_value
        output_topic_right = self.get_parameter('output_topic_right').get_parameter_value().string_value

        self.pub = self.create_publisher(Float64MultiArray, output_topic, 5)
        self.pub_left = self.create_publisher(Float64MultiArray, output_topic_left, 5)
        self.pub_right = self.create_publisher(Float64MultiArray, output_topic_right, 5)

        self.create_subscription(Float64MultiArray, input_topic, self.wheel_speed_callback, 5)

        self.received_kine_data = False
        self.timer = self.create_timer(0.5, self.check_kine_timeout)

        set_velocity_mode(SLAVE_ID_L)
        set_velocity_mode(SLAVE_ID_R)

    def wheel_speed_callback(self, msg):
        """Callback khi nhận được dữ liệu từ topic kine_to_ZLA8015D"""
        if len(msg.data) == 2:
            left_speed = msg.data[0]
            right_speed = msg.data[1]

            self.received_kine_data = True

            set_motor_speed(SLAVE_ID_L, chuyen_doi(left_speed), chuyen_doi(left_speed))
            set_motor_speed(SLAVE_ID_R, chuyen_doi(-right_speed), chuyen_doi(-right_speed))

            left_speed_front, left_speed_back = read_motor_speed(SLAVE_ID_L)
            right_speed_front, right_speed_back = read_motor_speed(SLAVE_ID_R)

            if None in (left_speed_front, left_speed_back, right_speed_front, right_speed_back):
                self.get_logger().error("Lỗi: Không thể đọc tốc độ phản hồi từ driver.")
                return

            stand_data = Float64MultiArray(data=[left_speed, right_speed])
            feedback_left = Float64MultiArray(data=[left_speed_front, left_speed_back])
            feedback_right = Float64MultiArray(data=[-right_speed_front, -right_speed_back])

            self.pub.publish(stand_data)
            self.pub_left.publish(feedback_left)
            self.pub_right.publish(feedback_right)

    def check_kine_timeout(self):
        """Nếu không nhận được dữ liệu từ topic kine_to_ZLA8015D, dừng robot"""
        if not self.received_kine_data:
            print("Không nhận được dữ liệu từ kine_to_ZLA8015D, dừng robot!")

            set_motor_speed(SLAVE_ID_L, 0, 0)
            set_motor_speed(SLAVE_ID_R, 0, 0)

            stand_data = Float64MultiArray(data=[0.0, 0.0])
            feedback_left = Float64MultiArray(data=[0.0, 0.0])
            feedback_right = Float64MultiArray(data=[0.0, 0.0])

            self.pub.publish(stand_data)
            self.pub_left.publish(feedback_left)
            self.pub_right.publish(feedback_right)

        self.received_kine_data = False

def main(args=None):
    rclpy.init(args=args)
    node = ZLA8015DDriverNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    modbus_client.close()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

