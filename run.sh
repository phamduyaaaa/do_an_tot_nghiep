#!/bin/bash

# ==============================================================================
# Robotics & IL Dashboard Master Launcher
#
# Purpose: Orchestrates micro-ROS, hardware bringup, and Streamlit UI.
# Usage:   ./run_system.sh
# ==============================================================================

# Get the absolute root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- FUNCTION: STOP ALL PROCESSES ---
stop_all() {
    echo -e "\n[INFO] Sweeping and force-killing all spawned processes..."
    
    # Kill by pattern to ensure all child shells are closed
    pkill -9 -f "micro_ros_agent" 2>/dev/null
    pkill -9 -f "bringup.launch.py" 2>/dev/null
    pkill -9 -f "streamlit" 2>/dev/null
    
    # Release the serial port
    fuser -k -9 /dev/ttyUSB0 >/dev/null 2>&1
    
    sleep 1 
}

# --- FUNCTION: CLEANUP AND EXIT ---
cleanup_and_exit() {
    stop_all
    echo "[INFO] Successfully closed! Exiting."
    exit 0
}

# Trap signals for graceful shutdown
trap cleanup_and_exit INT TERM

# --- FUNCTION: START THE SYSTEM ---
start_system() {
    local SESSION_TIME
    SESSION_TIME=$(date +"%Y-%m-%d_%H-%M-%S")
    local LOG_DIR="$ROOT_DIR/run_logs/$SESSION_TIME"
    mkdir -p "$LOG_DIR"

    echo "================================================"
    echo "STARTING ROBOTICS SYSTEM & IL DASHBOARD"
    echo "Session Logs: run_logs/$SESSION_TIME/"
    echo "================================================"

    local USE_TERMINATOR=false
    if command -v terminator >/dev/null 2>&1; then
        echo "[INFO] Terminator detected!"
        USE_TERMINATOR=true
    else
        echo "[WARNING] Terminator not found. Using gnome-terminal."
    fi

    # --- FIND APP ---
    local APP_DIR
    if [[ -f "$ROOT_DIR/imitation_learning/app.py" ]]; then
        APP_DIR="$ROOT_DIR/imitation_learning"
    elif [[ -f "$ROOT_DIR/app.py" ]]; then
        APP_DIR="$ROOT_DIR"
    else
        echo "[ERROR] app.py not found!"
        exit 1
    fi

    local APP_FILE="$APP_DIR/app.py"

    # --- STEP 1: WORKSPACE CHECK ---
    echo -e "\n[1/3] Checking workspace..."
    cd "$ROOT_DIR/skid_hardware_ws" || exit 1

    if [[ ! -d "install" ]]; then
        colcon build --parallel-workers 1 \
            --cmake-args -DCMAKE_BUILD_PARALLEL_LEVEL=1
    fi

    # shellcheck disable=SC1091
    source install/setup.bash

    # --- COMMANDS (FIXED) ---
    local CMD_AGENT="cd '$ROOT_DIR/skid_hardware_ws'; \
source install/setup.bash; \
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 2>&1 | \
tee '$LOG_DIR/agent.log'; exec bash"

    local CMD_BRINGUP="cd '$ROOT_DIR/skid_hardware_ws'; \
source install/setup.bash; \
ros2 launch bringup bringup.launch.py 2>&1 | \
tee '$LOG_DIR/bringup.log'; exec bash"

    local CMD_STREAMLIT="export PYTHONPATH='$APP_DIR':\$PYTHONPATH; \
cd '$APP_DIR'; \
python3 -m streamlit run '$APP_FILE' 2>&1 | \
tee '$LOG_DIR/streamlit.log'; exec bash"

    # --- STEP 2: LAUNCH ROS 2 ---
    echo -e "\n[2/3] Launching ROS2..."
    fuser -k /dev/ttyUSB0 >/dev/null 2>&1

    if [[ "$USE_TERMINATOR" == true ]]; then
        terminator -T "Micro-ROS Agent" -x bash -ic "$CMD_AGENT" &
        sleep 2
        terminator --new-tab -T "Bringup" -x bash -ic "$CMD_BRINGUP" &
    else
        gnome-terminal --title="Micro-ROS Agent" -- bash -ic "$CMD_AGENT" &
        sleep 2
        gnome-terminal --title="Bringup" -- bash -ic "$CMD_BRINGUP" &
    fi

    sleep 2

    # --- STEP 3: LAUNCH GUI ---
    echo -e "\n------------------------------------------------"
    read -rp "[?] Launch Streamlit GUI? (y/n) -> " confirm_gui

    if [[ "$confirm_gui" =~ ^[Yy]$ ]]; then
        echo "[3/3] Launching GUI..."
        if [[ "$USE_TERMINATOR" == true ]]; then
            terminator --new-tab -T "Streamlit" -x bash -ic "$CMD_STREAMLIT" &
        else
            gnome-terminal --title="Streamlit" -- bash -ic "$CMD_STREAMLIT" &
        fi
    else
        echo "[INFO] Skipped GUI."
    fi

    echo -e "\n================================================"
    echo "DONE!"
    echo "================================================"
}

# --- MAIN LOOP ---
start_system

while true; do
    echo -e "\n[r] Reset | [q] Quit"
    read -rp "Choose: " choice
    
    case "$choice" in 
        [rR] )
            stop_all
            start_system
            ;;
        [qQ] )
            cleanup_and_exit
            ;;
        * )
            echo "Invalid choice."
            ;;
    esac
done
