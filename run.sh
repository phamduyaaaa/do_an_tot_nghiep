#!/bin/bash

# Get the current working directory to ensure absolute paths
ROOT_DIR=$(pwd)

# Initialize process ID variables
PID_AGENT=""
PID_BRINGUP=""
PID_STREAMLIT=""

# --- FUNCTION: STOP ALL PROCESSES ---
stop_all() {
    echo ""
    echo "[INFO] Stopping current processes..."
    # Suppress error output if processes are already dead
    kill $PID_AGENT $PID_BRINGUP $PID_STREAMLIT 2>/dev/null
    sleep 1 # Give processes a moment to shut down gracefully
}

# --- FUNCTION: CLEANUP AND EXIT ---
# Catch Ctrl+C to safely kill background processes and exit the terminal
cleanup_and_exit() {
    stop_all
    echo "Successfully closed! Exiting."
    exit 0
}
trap cleanup_and_exit INT TERM

# --- FUNCTION: START THE SYSTEM ---
start_system() {
    echo "================================================"
    echo "STARTING ROBOTICS SYSTEM & IL DASHBOARD"
    echo "================================================"

    # --- STEP 1: SETUP WORKSPACE ---
    echo "[1/3] Checking skid_hardware_ws workspace..."
    cd "$ROOT_DIR/skid_hardware_ws" || { echo "Error: skid_hardware_ws directory not found"; exit 1; }

    if [ ! -d "install" ]; then
        echo "'install' directory not found. Starting build process..."
        colcon build --parallel-workers 1 --cmake-args -DCMAKE_BUILD_PARALLEL_LEVEL=1
    fi
    source install/setup.bash

    # --- STEP 2: LAUNCH ROS 2 (BACKGROUND) ---
    echo "[2/3] Launching Micro-ROS Agent and Bringup..."

    # Kill any process currently using the USB port (hide standard output/error)
    fuser -k /dev/ttyUSB0 >/dev/null 2>&1

    ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 &
    PID_AGENT=$!

    # Wait 2 seconds for the Agent to initialize
    sleep 2 

    ros2 launch bringup bringup.launch.py &
    PID_BRINGUP=$!

    # --- STEP 3: LAUNCH STREAMLIT GUI ---
    echo "[3/3] Launching Imitation Learning Dashboard..."

    cd "$ROOT_DIR/imitation_learning" || { echo "Error: imitation_learning directory not found"; exit 1; }

    streamlit run app.py &
    PID_STREAMLIT=$!

    echo "================================================"
    echo "DONE! System is up and running."
    echo "================================================"
}

# --- MAIN EXECUTION FLOW ---

# 1. Start the system for the first time
start_system

# 2. Interactive control loop (Replaces the 'wait' command)
while true; do
    echo ""
    echo "------------------------------------------------"
    echo "COMMAND MENU:"
    echo " [r] Type 'r' + Enter to RESET the system"
    echo " [q] Type 'q' + Enter (or Ctrl+C) to QUIT"
    echo "------------------------------------------------"
    
    # Wait for user input
    read -p "Choose an option: " choice
    
    case "$choice" in 
        r|R )
            echo "[!] Reset command received. Restarting..."
            stop_all
            start_system
            ;;
        q|Q )
            cleanup_and_exit
            ;;
        * )
            echo "Invalid option. Please type 'r' or 'q'."
            ;;
    esac
done
