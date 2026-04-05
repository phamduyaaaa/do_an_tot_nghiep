#!/bin/bash

# Get the current working directory
ROOT_DIR=$(pwd)

# --- FUNCTION: STOP ALL PROCESSES ---
stop_all() {
    echo ""
    echo "[INFO] Sweeping and force-killing all spawned processes..."
    
    # 1. Force kill the specific ROS and Streamlit processes
    pkill -9 -f "micro_ros_agent" 2>/dev/null
    pkill -9 -f "bringup.launch.py" 2>/dev/null
    pkill -9 -f "streamlit" 2>/dev/null
    
    # 2. Release the serial port completely
    fuser -k -9 /dev/ttyUSB0 >/dev/null 2>&1
    
    sleep 1 
}

# --- FUNCTION: CLEANUP AND EXIT ---
cleanup_and_exit() {
    stop_all
    echo "Successfully closed! Exiting."
    exit 0
}
trap cleanup_and_exit INT TERM

# --- FUNCTION: START THE SYSTEM ---
start_system() {
    # Create a unique timestamped folder for this specific run
    SESSION_TIME=$(date +"%Y-%m-%d_%H-%M-%S")
    LOG_DIR="$ROOT_DIR/run_logs/$SESSION_TIME"
    mkdir -p "$LOG_DIR"

    echo "================================================"
    echo "STARTING ROBOTICS SYSTEM & IL DASHBOARD"
    echo "Session Logs: run_logs/$SESSION_TIME/"
    echo "================================================"

    # --- STEP 1: SETUP WORKSPACE ---
    echo "[1/3] Checking skid_hardware_ws workspace..."
    cd "$ROOT_DIR/skid_hardware_ws" || { echo "Error: skid_hardware_ws directory not found"; exit 1; }

    if [ ! -d "install" ]; then
        echo "'install' directory not found. Starting build process..."
        colcon build --parallel-workers 1 --cmake-args -DCMAKE_BUILD_PARALLEL_LEVEL=1
    fi
    source install/setup.bash

    # --- STEP 2: LAUNCH ROS 2 (SEPARATE TERMINALS) ---
    echo "[2/3] Launching Micro-ROS Agent and Bringup in new windows..."

    fuser -k /dev/ttyUSB0 >/dev/null 2>&1

    # Spawn Terminal 1: Micro-ROS Agent (Log saved via 'tee')
    echo "      -> Spawning Agent Terminal..."
    gnome-terminal --title="Micro-ROS Agent" -- bash -c "ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 2>&1 | tee '$LOG_DIR/agent.log'"
    
    # Wait 2 seconds for the Agent to initialize
    sleep 2 

    # Spawn Terminal 2: Bringup Launch
    echo "      -> Spawning Bringup Terminal..."
    gnome-terminal --title="Bringup Node" -- bash -c "ros2 launch bringup bringup.launch.py 2>&1 | tee '$LOG_DIR/bringup.log'"

    sleep 2

    # --- STEP 3: LAUNCH STREAMLIT GUI ---
    echo ""
    echo "------------------------------------------------"
    while true; do
        read -p "[?] Proceed to launch the Streamlit GUI? (y/n) -> " confirm_gui
        case "$confirm_gui" in 
            y|Y )
                echo "[3/3] Launching Imitation Learning Dashboard..."
                cd "$ROOT_DIR/imitation_learning" || { echo "Error: imitation_learning directory not found"; exit 1; }
                
                # Spawn Terminal 3: Streamlit
                echo "      -> Spawning Streamlit Terminal..."
                gnome-terminal --title="IL Dashboard (Streamlit)" -- bash -c "streamlit run app.py 2>&1 | tee '$LOG_DIR/streamlit.log'"
                break
                ;;
            n|N )
                echo "[INFO] Skipping Streamlit GUI launch."
                break
                ;;
            * )
                echo "Invalid input. Please enter 'y' or 'n'."
                ;;
        esac
    done

    echo "================================================"
    echo "DONE! System initialization complete."
    echo "================================================"
}

# --- MAIN EXECUTION FLOW ---

start_system

# Interactive control loop
while true; do
    echo ""
    echo "------------------------------------------------"
    echo "COMMAND MENU:"
    echo " [r] Type 'r' + Enter to RESET the system"
    echo " [q] Type 'q' + Enter (or Ctrl+C) to QUIT"
    echo "------------------------------------------------"
    
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
