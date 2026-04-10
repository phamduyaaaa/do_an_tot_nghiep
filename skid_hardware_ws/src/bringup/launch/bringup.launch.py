from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    return LaunchDescription([
        IncludeLaunchDescription(
            FindPackageShare('low_control').find('low_control') + '/launch/low_level_control.launch.xml'
        ),
        IncludeLaunchDescription(
            FindPackageShare('velodyne').find('velodyne') + '/launch/velodyne-all-nodes-VLP16-launch.py'
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='base_link_to_velodyne_tf',
            arguments=['0', '0', '0.15', '0', '0', '0', 'base_footprint', 'base_link']
        ),

        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='base_link_to_velodyne_tf',
            arguments=['0.1', '0', '0.48', '0', '0', '0', 'base_link', 'velodyne']
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='base_link_to_imu_tf',
            arguments=['0', '0', '0.', '0', '0', '0', 'base_link', 'imu_link']
        ),
    ])
