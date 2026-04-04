"""
================================================================================
Imitation Learning Control Panel (Streamlit Web UI)

* Purpose: Centralized dashboard to manage data collection, training, and 
           inference for the robotics behavior cloning pipeline.
* Inputs:  Hyperparameters and file paths configured via the UI.
* Outputs: Real-time execution logs, saved models, and metric plots.
* Usage:   Run `streamlit run app.py` in the terminal.
================================================================================
"""

import streamlit as st
import subprocess
import os
import glob

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Do an tot nghiep", 
    page_icon="🤖", 
    layout="wide"
)

# --- DIRECTORY SETUP ---
# Ensure required directories exist to prevent errors
for folder in ['logs', 'checkpoints', 'plots']:
    os.makedirs(folder, exist_ok=True)

# --- UTILS ---
def get_files(directory, extension):
    """Recursively finds all files with a specific extension in a directory."""
    files = []
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            if f.endswith(extension):
                # Replace backslashes for Windows compatibility
                files.append(os.path.join(root, f).replace('\\', '/'))
    return files

def run_script_realtime(command):
    """Executes a terminal command and displays output in real-time."""
    st.info(f"Running command: `{command}`")
    log_container = st.empty()
    logs = ""
    
    try:
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            logs += line
            log_container.code(logs, language="bash")
            
        process.wait()
        
        if process.returncode == 0:
            st.success("Process completed successfully!")
        else:
            st.error(f"Process failed (Exit code: {process.returncode})")
            
    except Exception as e:
        st.error(f"Execution error: {e}")

# --- MAIN APP ---
def main():
    st.sidebar.title("IL Control Panel")
    st.sidebar.markdown("---")
    
    menu = ["1. Data Collection", "2. DAgger Collection", "3. Train Model", "4. Train & Plot Loss", "5. Inference"]
    choice = st.sidebar.radio("Select Workflow:", menu)

    st.title(choice)

    # ---------------------------------------------------------
    # 1. NORMAL DATA COLLECTION
    # ---------------------------------------------------------
    if choice == "1. Data Collection":
        st.write("Collect expert demonstrations (Behavior Cloning).")
        
        col1, col2 = st.columns(2)
        with col1:
            out_name = st.text_input("Output File Name:", value="dataset.csv")
            downsample = st.number_input("Downsample size:", value=180)
        with col2:
            rate = st.number_input("Rate (Hz):", value=20)
            max_range = st.number_input("Max Range (m):", value=3.5)
            
        out_path = f"logs/{out_name}"
        
        if st.button("Start Collection", type="primary"):
            cmd = f"python3 scripts/data_collector.py --out {out_path} --downsample {downsample} --rate {rate} --max_range {max_range}"
            run_script_realtime(cmd)

    # ---------------------------------------------------------
    # 2. DAGGER DATA COLLECTION
    # ---------------------------------------------------------
    elif choice == "2. DAgger Collection":
        st.write("Collect data only when the robot is near obstacles (DAgger-lite).")
        
        col1, col2 = st.columns(2)
        with col1:
            out_name = st.text_input("Output File Name:", value="dagger_dataset.csv")
            danger_dist = st.number_input("Danger Distance (m):", value=0.6, step=0.1)
        with col2:
            cooldown = st.number_input("Cooldown steps:", value=5)
            rate = st.number_input("Rate (Hz):", value=20)
            
        out_path = f"logs/{out_name}"

        if st.button("Start DAgger", type="primary"):
            cmd = f"python3 scripts/data_collector_DAgger.py --out {out_path} --danger_dist {danger_dist} --cooldown {cooldown} --rate {rate}"
            run_script_realtime(cmd)

    # ---------------------------------------------------------
    # 3. TRAIN MODEL
    # ---------------------------------------------------------
    elif choice == "3. Train Model":
        st.write("Train the Policy Network using collected logs.")
        
        # Scan for datasets
        datasets = get_files("logs", ".csv")
        if not datasets:
            st.warning("No CSV datasets found in the `logs/` directory.")
            return
            
        selected_data = st.selectbox("Select Dataset:", datasets)
        out_model_name = st.text_input("Save Model As:", value="bc_model.pth")
        
        col1, col2 = st.columns(2)
        with col1:
            epochs = st.number_input("Epochs:", min_value=1, value=100)
            batch = st.selectbox("Batch Size:", [16, 32, 64, 128], index=2)
        with col2:
            lr = st.number_input("Learning Rate:", format="%.5f", value=0.001, step=0.0001)
            input_dim = st.number_input("Input Dimension:", value=180)
            
        out_path = f"checkpoints/{out_model_name}"

        if st.button("Start Training", type="primary"):
            cmd = f"python3 scripts/train.py --data {selected_data} --output {out_path} --epochs {epochs} --batch {batch} --lr {lr} --input_dim {input_dim}"
            run_script_realtime(cmd)

    # ---------------------------------------------------------
    # 4. TRAIN & PLOT LOSS
    # ---------------------------------------------------------
    elif choice == "4. Train & Plot Loss":
        st.write("Train the model and generate a Mean Squared Error (MSE) loss curve.")
        
        datasets = get_files("logs", ".csv")
        if not datasets:
            st.warning("No CSV datasets found in the `logs/` directory.")
            return
            
        selected_data = st.selectbox("Select Dataset:", datasets, key="plot_data")
        out_model_name = st.text_input("Save Model As:", value="bc_model_plot.pth", key="plot_model")
        epochs = st.number_input("Epochs:", min_value=1, value=50, key="plot_epochs")
        
        out_path = f"checkpoints/{out_model_name}"
        base_name = out_model_name.replace(".pth", "")
        expected_plot_path = f"plots/{base_name}_loss.png"

        if st.button("Train & Generate Plot", type="primary"):
            cmd = f"python3 scripts/train_plot.py --data {selected_data} --output {out_path} --epochs {epochs}"
            run_script_realtime(cmd)
            
            if os.path.exists(expected_plot_path):
                st.image(expected_plot_path, caption="Training Loss Curve")
            else:
                st.warning("Plot image not found.")

    # ---------------------------------------------------------
    # 5. INFERENCE
    # ---------------------------------------------------------
    elif choice == "5. Inference":
        st.write("Run the trained policy on the robot/simulation.")
        
        # Scan for models
        models = get_files("checkpoints", ".pth")
        if not models:
            st.warning("No .pth models found in the `checkpoints/` directory.")
            return
            
        selected_model = st.selectbox("Select Model:", models)
        
        col1, col2 = st.columns(2)
        with col1:
            downsample = st.number_input("Downsample size:", value=180, key="inf_ds")
        with col2:
            rate = st.number_input("Rate (Hz):", value=20, key="inf_rate")

        if st.button("Start Inference", type="primary"):
            cmd = f"python3 scripts/inference.py --model {selected_model} --downsample {downsample} --rate {rate}"
            run_script_realtime(cmd)

if __name__ == "__main__":
    main()
