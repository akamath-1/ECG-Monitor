import os
import subprocess
import time
from datetime import datetime

# === Import local modules ===
# Data generation module
from python.pipeline.step1_generate_dataset_ad8232 import (
    main as generate_dataset_ad8232_main,
)

# Firmware flashing modules
from python.pipeline.step2_flash_firmware_ble import (
    main as generate_and_flash_firmware_ble,
)
from python.pipeline.step2_flash_firmware_usb import (
    main as generate_and_flash_firmware_usb,
)


# Batch processing modules
from python.pipeline.step3_batchprocess import main as batch_test_main

# Data validation modules
from python.validation.compare_rpeak_bpm_ad8232 import main as compare_data_main

# Output dir
from python.pipeline.config import get_output_dir


# # FILE DESCRIPTION
# CONDITION = "walk_new_electrodes_on_chest_and_ribs"  # or "movement", "post_exercise"
# RUN_NUMBER = 2
# DURATION_SEC = 30
# SAMPLING_RATE = 250
# TARGET_SAMPLES = DURATION_SEC * SAMPLING_RATE
# data_file_name_base = (
#     f"ad8232_{CONDITION}_run{RUN_NUMBER}_{DURATION_SEC}_{SAMPLING_RATE}"
# )

# === PATHS =============================
STREAM_SCRIPT_USB = os.path.join(os.path.dirname(__file__), "step4_stream_usb.py")
STREAM_SCRIPT_BLE = os.path.join(os.path.dirname(__file__), "step4_stream_ble.py")
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def collect_user_input_test_file():
    while True:
        data_file_name_base = (
            input(
                "What is the file name of the AD8232 pre-recorded dataset you would like to test?: "
            )
            .strip()
            .lower()
        )
        input_csv = f"{data_file_name_base}.csv"
        # Check if AD8232 dataset file exists
        input_path = os.path.join(project_root, "datasets", "AD8232 Data", input_csv)
        if os.path.exists(input_path):
            print(f"✅ AD8232 dataset found: {input_csv}")
            break
        else:
            print(
                f"AD8232 dataset not found for {input_csv}. Please enter a valid file name or run data collection for the desired test condition (python3 python/pipeline/hardware/collect_ad8232_data.py)."
            )

    return data_file_name_base, input_csv


def collect_user_input_USB_BLE():
    while True:
        data_transport_method = (
            input(
                "Would you like to test with USB streaming or BLE streaming? Please enter USB or BLE."
            )
            .strip()
            .lower()
        )

        if data_transport_method == "usb" or data_transport_method == "ble":
            print(
                f"Accepted. Automated testing will be performed with streaming over {data_transport_method.upper()}."
            )
            return data_transport_method
        else:
            print(
                f'{data_transport_method} is not a valid entry. Please enter "USB" or "BLE" to proceed. '
            )


def run_full_pipeline():

    print("\n🚀 Starting full AD8232 ECG processing pipeline...\n")
    # print(f"   Condition: {CONDITION}")
    # print(f"   Run: {RUN_NUMBER}")
    # print(f"   Duration: {DURATION_SEC}s at {SAMPLING_RATE}Hz\n")

    data_file_name_base, input_csv = collect_user_input_test_file()
    data_transport_method = collect_user_input_USB_BLE()
    # OUTPUT DIRECTORY FOR THIS RUN:
    output_dir = os.path.join(
        project_root, "data_logs", "AD8232", data_file_name_base, data_transport_method.upper()
    )
    os.makedirs(output_dir, exist_ok=True)

    print(f"✅ Output directory: {output_dir}")
    # === STEP 1: Converting data to digital form ===

    # ADD SOMETHING HERE THAT ALLOWS USER TO ACCEPT OR REJECT COLLECTED DATASET AND TRY AGAIN OR QUIT
    print("=== STEP 1: Converting ECG data to digital form ===")
    digital_dataset = generate_dataset_ad8232_main(
        input_csv, output_csv_path=output_dir
    )
    print("Digital dataset successfully generated.")

    print("=== STEP 2: Generating firmware file and flashing it to ESP32")
    if data_transport_method == "usb":
        result_flash = generate_and_flash_firmware_usb(
            digital_dataset=digital_dataset, file_id=data_file_name_base
        )
    elif data_transport_method == "ble":
        result_flash = generate_and_flash_firmware_ble(
            digital_dataset=digital_dataset, file_id=data_file_name_base
        )

    if result_flash == None:
        print("Issue with firmware flashing. Aborting run.")
        return
    print("✅ Firmware flashing complete.\n")

    # === STEP 3: Run batch processing ===
    print("=== STEP 3: Running batch processing ===")
    batch_test_main(
        file_name=None, output_csv_path=output_dir, digital_dataset=digital_dataset
    )  # This saves the batch processed outputs
    print("✅ Batch processing complete.\n")

    # === STEP 4: Stream data from MCU ===
    print("=== STEP 4: Running MCU streaming ===")
    print(
        "🧠 Note: This will open the real-time ECG GUI. Close the window when done to continue."
    )
    time.sleep(2)
    if data_transport_method == "usb":
        subprocess.run(
            ["python3", STREAM_SCRIPT_USB, output_dir], cwd=project_root
        )  # add project_root to make sure it is running from project root, not working directory
    elif data_transport_method == "ble":
        subprocess.run(
            ["python3", STREAM_SCRIPT_BLE, output_dir], cwd=project_root
        )  # add project_root to make sure it is running from project root, not working directory

    print("✅ Streaming complete.\n")

    # === STEP 5: Graph and compare ===
    print("=== STEP 5: Generating comparison graphs ===")
    plot_save_path = os.path.join(output_dir, "comparison_plot.png")
    compare_data_main(csv_logs_folder_path=output_dir, save_path=plot_save_path)
    print("✅ Graph generation complete.\n")

    print("🎯 Full ECG pipeline completed successfully!")


if __name__ == "__main__":

    run_full_pipeline()
