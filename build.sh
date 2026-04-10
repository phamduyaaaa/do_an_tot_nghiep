#!/bin/bash

# ==============================================================================
# Workspace Build Script for skid_hardware_ws
#
# Purpose: Clean and rebuild the ROS 2 workspace with resource constraints.
# Usage:   ./build.sh (Run from the project root)
# ==============================================================================

# Get the current working directory to ensure absolute paths
ROOT_DIR=$(pwd)

echo "================================================"
echo "STARTING WORKSPACE BUILD PROCESS"
echo "================================================"

# --- STEP 1: NAVIGATE TO WORKSPACE ---
echo "[1/2] Navigating to skid_hardware_ws..."
cd "${ROOT_DIR}/skid_hardware_ws" || {
    echo "Error: skid_hardware_ws directory not found"
    exit 1
}

# --- STEP 2: CHECK EXISTING BUILD ---
# Check if any build artifacts already exist
if [[ -d "build" || -d "install" || -d "log" ]]; then
    echo "------------------------------------------------"
    echo "[!] Existing build directories found."
    
    # Prompt the user for a decision
    read -rp "Do you want to clean old files and rebuild? (y/N): " choice
    
    case "$choice" in 
        [yY] )
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

# --- STEP 3: BUILD WORKSPACE ---
echo "[2/2] Running colcon build..."
# Constraint: Limited to 1 worker to prevent OOM (Out of Memory) on small systems
colcon build \
    --parallel-workers 1 \
    --cmake-args -DCMAKE_BUILD_PARALLEL_LEVEL=1

# --- STEP 4: CHECK RESULT ---
# shellcheck disable=SC2181
if [[ $? -eq 0 ]]; then
    echo "================================================"
    echo "DONE! Workspace built successfully."
    echo "================================================"
else
    echo "================================================"
    echo "BUILD FAILED! Please check the error logs above."
    echo "================================================"
    exit 1
fi
