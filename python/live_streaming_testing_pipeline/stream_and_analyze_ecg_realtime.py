import os
import subprocess
import time
from datetime import datetime

# === Import local modules ===

from python.pipeline.step1_generate_dataset_ad8232 import (
    main as generate_dataset_ad8232_main,
)
from python.pipeline.step2_flash_firmware_realtime import (
    main as generate_and_flash_firmware,
)
from python.pipeline.step4_batchprocess_ecg_realtime import main as batch_test_main
from python.validation.compare_rpeak_bpm_ad8232_livestreamed import (
    main as compare_ad8232_data_main_livestreamed,
)
from python.pipeline.config import get_output_dir

# FILE DESCRIPTION
CONDITION = "walk_new_electrodes_on_chest_and_ribs"  # or "movement", "post_exercise"
RUN_NUMBER = 2
DURATION_SEC = 30
SAMPLING_RATE = 250
TARGET_SAMPLES = DURATION_SEC * SAMPLING_RATE
data_file_name_base = (
    f"ad8232_{CONDITION}_run{RUN_NUMBER}_{DURATION_SEC}_{SAMPLING_RATE}"
)

# === PATHS =============================
STREAM_SCRIPT = os.path.join(os.path.dirname(__file__), "step3_stream_ble_realtime.py")
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


# OUTPUT DIRECTORY FOR THIS RUN:
output_dir = os.path.join(
    project_root, "data_logs", "ECG Real-Time", data_file_name_base
)
os.makedirs(output_dir, exist_ok=True)

print(f"Output directory for data logs: {output_dir}")


def run_full_pipeline():

    print("\n🚀 Starting full AD8232 ECG live-streaming pipeline...\n")
    print(f"   Condition: {CONDITION}")
    print(f"   Run: {RUN_NUMBER}")
    print(f"   Duration: {DURATION_SEC}s at {SAMPLING_RATE}Hz\n")

    # CREATE FILE PATH AND FOLDER HERE FOR ALL DATA TO GO INTO

    # change this step to flash a new firmware file to the ESP32
    print("=== STEP 1: Generating firmware file and flashing it to ESP32")
    result_flash = generate_and_flash_firmware()
    if result_flash == None:
        print("Issue with firmware flashing. Aborting run.")
        return
    print("✅ Firmware flashing complete.\n")

    # THIS STEP NEEDS TO NOW OUTPUT A CSV WITH THE FULL DATA THAT CAN BE PASSED INTO BATCH PROCESSING
    # === STEP 4: Stream data from MCU ===
    print("=== STEP 2: Running MCU streaming ===")
    print(
        "🧠 Note: This will open the real-time ECG GUI. Close the window when done to continue."
    )
    time.sleep(2)
    subprocess.run(
        ["python3", STREAM_SCRIPT, output_dir], cwd=project_root
    )  # add project_root to make sure it is running from project root, not working directory
    print("✅ Streaming complete.\n")
    csv_path = os.path.join(output_dir, "streamed_raw_packets.csv")
    # === STEP 3: Run batch processing ===
    print("=== STEP 3: Running batch processing ===")
    batch_test_main(
        csv_file_path=csv_path, output_csv_path=output_dir
    )  # This saves the batch processed outputs
    print("✅ Batch processing complete.\n")

    # === STEP 5: Graph and compare ===
    print("=== STEP 5: Generating comparison graphs ===")
    plot_save_path = os.path.join(output_dir, "comparison_plot.png")
    compare_ad8232_data_main_livestreamed(
        csv_logs_folder_path=output_dir, save_path=plot_save_path
    )
    print("✅ Graph generation complete.\n")

    print("🎯 Full ECG pipeline completed successfully!")


if __name__ == "__main__":

    run_full_pipeline()
