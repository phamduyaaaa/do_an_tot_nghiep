from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource  
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                FindPackageShare('low_control').find('low_control') + '/launch/low_level_control.launch.xml'
            )
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                FindPackageShare('velodyne').find('velodyne') + '/launch/velodyne-all-nodes-VLP16-launch.py'
            )
        ),
    ])
