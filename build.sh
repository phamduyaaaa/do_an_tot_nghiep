#!/bin/bash

# Get the current working directory to ensure absolute paths
ROOT_DIR=$(pwd)

echo "================================================"
echo "STARTING WORKSPACE BUILD PROCESS"
echo "================================================"

# --- STEP 1: NAVIGATE TO WORKSPACE ---
echo "[1/2] Navigating to skid_hardware_ws..."
cd "$ROOT_DIR/skid_hardware_ws" || { echo "Error: skid_hardware_ws directory not found"; exit 1; }

# --- STEP 1.5: CHECK EXISTING BUILD ---
# Check if any of the build artifacts already exist
if [ -d "build" ] || [ -d "install" ] || [ -d "log" ]; then
    echo "------------------------------------------------"
    echo "[!] Existing build directories found."
    
    # Prompt the user for a decision
    read -p "Do you want to clean old files and rebuild? (y/N): " choice
    
    case "$choice" in 
        y|Y )
            echo "Cleaning old build, install, and log directories..."
            rm -rf build install log
            echo "Cleaned successfully."
            echo "------------------------------------------------"
            ;;
        * )
            echo "Build skipped. Exiting."
            exit 0
            ;;
    esac
fi

# --- STEP 2: BUILD WORKSPACE ---
echo "[2/2] Running colcon build..."
# Note: Limited to 1 worker to prevent freezing on systems with limited RAM
colcon build --parallel-workers 1 --cmake-args -DCMAKE_BUILD_PARALLEL_LEVEL=1

# --- STEP 3: CHECK RESULT ---
# $? stores the exit status of the last command (0 means success)
if [ $? -eq 0 ]; then
    echo "================================================"
    echo "DONE! Workspace built successfully."
    echo "================================================"
else
    echo "================================================"
    echo "BUILD FAILED! Please check the error logs above."
    echo "================================================"
    exit 1
fi
