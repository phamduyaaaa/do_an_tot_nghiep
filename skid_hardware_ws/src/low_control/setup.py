from setuptools import find_packages, setup

package_name = 'low_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/ps3.launch.xml']),
        ('share/' + package_name + '/launch', ['launch/low_level_control.launch.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='minh2',
    maintainer_email='minh2@todo.todo',
    description='Package for controlling low-level robot functions',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ZLA8015D_pub = low_control.ZLA8015D_pub:main',
            'kinematic = low_control.kinematic:main',
        ],
    },
)
