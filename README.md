# Do An Tot Nghiep


## How to use?

```bash
# Check skid_hardware_ws workspace
# If it is not built, the system will automatically build it
# You can also use this script to rebuild
bash build.sh
```

```bash
# Run the system in 3 steps:

# Step 1: Check Terminator
# - If available -> use Terminator
# - Otherwise -> fallback to default Terminal

# Step 2: Launch skid_hardware_ws

# Step 3: If Step 2 is successful -> confirm to run Streamlit App (localhost)
bash run.sh
```
### NOTE:
#### If nothing happens after running the scripts, DO NOT assume success.
#### Please check logs, ports, and device connections.
### Inference:
#### Choose checkpoints/28-11_sanha10T2_slow.pth (This checkpoints can download in [Download checkpoint](https://github.com/phamduyaaaa/do_an_tot_nghiep/releases/tag/sanh_a10_t2_slow_28_11_25)
### TIP:
#### You can access Streamlit from any device connected to the same Wi-Fi network as your laptop.
## Project Information
- **Author:** Pham Duc Duy
- **Contact:** duypham.robotics@gmail.com
- **Last updated:** 2026-04-06


