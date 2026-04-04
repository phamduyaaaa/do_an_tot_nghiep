#!/bin/bash

# Get the current working directory to ensure absolute paths
ROOT_DIR=$(pwd)

# --- CLEANUP FUNCTION ---
# Catch Ctrl+C to safely kill all background processes
cleanup() {
    echo ""
    echo "Shutting down the entire system..."
    kill $PID_AGENT $PID_BRINGUP $PID_STREAMLIT 2>/dev/null
    echo "Successfully closed!"
    exit
}
trap cleanup INT TERM

echo "================================================"
echo "STARTING ROBOTICS SYSTEM & IL DASHBOARD"
echo "================================================"

# --- STEP 1: SETUP WORKSPACE ---
echo "[1/3] Checking skid_hardware_ws workspace..."
cd "$ROOT_DIR/skid_hardware_ws" || { echo "Error: skid_hardware_ws directory not found"; exit 1; }

# Check if the project is built
if [ ! -d "install" ]; then
    echo "'install' directory not found. Starting build process..."
    colcon build --parallel-workers 1 --cmake-args -DCMAKE_BUILD_PARALLEL_LEVEL=1
else
    echo "Build found (install directory exists)."
fi

source install/setup.bash

# --- STEP 2: LAUNCH ROS 2 (BACKGROUND) ---
echo "[2/3] Launching Micro-ROS Agent and Bringup..."

# Run Micro-ROS Agent in the background
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 &
PID_AGENT=$!  # Save process ID for cleanup

# Wait 2 seconds for the Agent to initialize before launching bringup
sleep 2 

ros2 launch bringup bringup.launch.py &
PID_BRINGUP=$!

# --- STEP 3: LAUNCH STREAMLIT GUI ---
echo "[3/3] Launching Imitation Learning Dashboard..."

# Navigate to the IL directory
cd "$ROOT_DIR/imitation_learning" || { echo "Error: imitation_learning directory not found"; exit 1; }

streamlit run main.py &
PID_STREAMLIT=$!

echo "================================================"
echo "DONE! System is up and running."
echo "PRESS Ctrl+C TO STOP ALL PROCESSES"
echo "================================================"

# Wait command prevents the script from exiting immediately
wait
