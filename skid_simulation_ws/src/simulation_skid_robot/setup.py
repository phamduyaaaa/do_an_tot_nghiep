import os
from glob import glob

from setuptools import setup

package_name = 'simulation'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),

        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.urdf')),
        (os.path.join('share', package_name, 'meshes/visual'), glob('meshes/visual/*.STL')),

    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Pham Duc Duy',
    maintainer_email='duypham.robotics@gmail.com',
    description='Skidsteer Robot Simulation Package',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
