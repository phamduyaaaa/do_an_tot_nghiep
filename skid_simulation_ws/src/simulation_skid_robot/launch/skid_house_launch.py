import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_name = 'simulation'
    bringup_dir = get_package_share_directory(pkg_name)

    urdf_file_name = 'skid_robot_v3.urdf'
    urdf_path = os.path.join(bringup_dir, 'urdf', urdf_file_name)

    tb3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')
    world_path = os.path.join(tb3_gazebo_dir, 'worlds', 'turtlebot3_house.world')

    install_dir = get_package_share_directory(pkg_name).split('/share')[0]
    gazebo_model_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=[os.path.join(install_dir, 'share'),
               ':', os.environ.get('GAZEBO_MODEL_PATH', '')]
    )

    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={
            'world': world_path,  # Hoặc bỏ dòng này để load empty world
            'verbose': 'true',
            'pause': 'false'
        }.items()
    )

    with open(urdf_path) as infp:
        robot_desc = infp.read()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[{
            'use_sim_time': True,
            'robot_description': robot_desc
        }]
    )

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'my_robot',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.5'
        ],
        output='screen'
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    return LaunchDescription([
        gazebo_model_path,
        gzserver,
        robot_state_publisher,
        spawn_entity,
        joint_state_publisher,
    ])
