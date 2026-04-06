#!/bin/bash

# Get the absolute root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- FUNCTION: STOP ALL PROCESSES ---
stop_all() {
    echo ""
    echo "[INFO] Sweeping and force-killing all spawned processes..."
    
    pkill -9 -f "micro_ros_agent" 2>/dev/null
    pkill -9 -f "bringup.launch.py" 2>/dev/null
    pkill -9 -f "streamlit" 2>/dev/null
    
    fuser -k -9 /dev/ttyUSB0 >/dev/null 2>&1
    
    sleep 1 
}

# --- FUNCTION: CLEANUP AND EXIT ---
cleanup_and_exit() {
    stop_all
    echo "[INFO] Successfully closed! Exiting."
    exit 0
}
trap cleanup_and_exit INT TERM

# --- FUNCTION: START THE SYSTEM ---
start_system() {
    SESSION_TIME=$(date +"%Y-%m-%d_%H-%M-%S")
    LOG_DIR="$ROOT_DIR/run_logs/$SESSION_TIME"
    mkdir -p "$LOG_DIR"

    echo "================================================"
    echo "STARTING ROBOTICS SYSTEM & IL DASHBOARD"
    echo "Session Logs: run_logs/$SESSION_TIME/"
    echo "================================================"

    USE_TERMINATOR=false
    if command -v terminator >/dev/null 2>&1; then
        echo "[INFO] Terminator detected!"
        USE_TERMINATOR=true
    else
        echo "[WARNING] Terminator not found. Using gnome-terminal."
    fi

    # --- FIND APP ---
    if [ -f "$ROOT_DIR/imitation_learning/app.py" ]; then
        APP_DIR="$ROOT_DIR/imitation_learning"
    elif [ -f "$ROOT_DIR/app.py" ]; then
        APP_DIR="$ROOT_DIR"
    else
        echo "[ERROR] app.py not found!"
        exit 1
    fi

    APP_FILE="$APP_DIR/app.py"

    # --- STEP 1 ---
    echo ""
    echo "[1/3] Checking workspace..."
    cd "$ROOT_DIR/skid_hardware_ws" || exit 1

    if [ ! -d "install" ]; then
        colcon build --parallel-workers 1 --cmake-args -DCMAKE_BUILD_PARALLEL_LEVEL=1
    fi

    source install/setup.bash

    # --- COMMANDS (FIXED) ---
    CMD_AGENT="cd '$ROOT_DIR/skid_hardware_ws'; source install/setup.bash; ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 2>&1 | tee '$LOG_DIR/agent.log'; exec bash"

    CMD_BRINGUP="cd '$ROOT_DIR/skid_hardware_ws'; source install/setup.bash; ros2 launch bringup bringup.launch.py 2>&1 | tee '$LOG_DIR/bringup.log'; exec bash"

    CMD_STREAMLIT="export PYTHONPATH='$APP_DIR':\$PYTHONPATH; \
    cd '$APP_DIR'; \
    python3 -c \"import os; os.chdir('$APP_DIR'); import subprocess; subprocess.run(['streamlit','run','$APP_FILE'])\" \
    2>&1 | tee '$LOG_DIR/streamlit.log'; exec bash"

    # --- STEP 2 ---
    echo ""
    echo "[2/3] Launching ROS2..."

    fuser -k /dev/ttyUSB0 >/dev/null 2>&1

    if [ "$USE_TERMINATOR" = true ]; then
        terminator -T "Micro-ROS Agent" -x bash -ic "$CMD_AGENT" &
        sleep 2
        terminator --new-tab -T "Bringup" -x bash -ic "$CMD_BRINGUP" &
    else
        gnome-terminal --title="Micro-ROS Agent" -- bash -ic "$CMD_AGENT" &
        sleep 2
        gnome-terminal --title="Bringup" -- bash -ic "$CMD_BRINGUP" &
    fi

    sleep 2

    # --- STEP 3 ---
    echo ""
    echo "------------------------------------------------"
    read -p "[?] Launch Streamlit GUI? (y/n) -> " confirm_gui

    if [[ "$confirm_gui" =~ ^[Yy]$ ]]; then
        echo "[3/3] Launching GUI..."

        if [ "$USE_TERMINATOR" = true ]; then
            terminator --new-tab -T "Streamlit" -x bash -ic "$CMD_STREAMLIT" &
        else
            gnome-terminal --title="Streamlit" -- bash -ic "$CMD_STREAMLIT" &
        fi
    else
        echo "[INFO] Skipped GUI."
    fi

    echo "================================================"
    echo "DONE!"
    echo "================================================"
}

# --- MAIN ---
start_system

while true; do
    echo ""
    echo "[r] Reset | [q] Quit"
    read -p "Choose: " choice
    
    case "$choice" in 
        r|R )
            stop_all
            start_system
            ;;
        q|Q )
            cleanup_and_exit
            ;;
    esac
done
