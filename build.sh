#!/bin/bash

# Get the current working directory to ensure absolute paths
ROOT_DIR=$(pwd)

echo "================================================"
echo "STARTING WORKSPACE BUILD PROCESS"
echo "================================================"

# --- STEP 1: NAVIGATE TO WORKSPACE ---
echo "[1/2] Navigating to skid_hardware_ws..."
cd "$ROOT_DIR/skid_hardware_ws" || { echo "Error: skid_hardware_ws directory not found"; exit 1; }

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
