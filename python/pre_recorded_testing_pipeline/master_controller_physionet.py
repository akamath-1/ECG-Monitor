import os
import subprocess
import time
from datetime import datetime

# === Import local modules ===
# Data generation module
from python.pre_recorded_testing_pipeline.step1_generate_dataset_physionet import (
    main as generate_dataset_main,
)

# Firmware flashing modules
from python.pre_recorded_testing_pipeline.step2_flash_firmware_ble import (
    main as generate_and_flash_firmware_ble,
)
from python.pre_recorded_testing_pipeline.step2_flash_firmware_usb import (
    main as generate_and_flash_firmware_usb,
)


# Batch processing modules
from python.pre_recorded_testing_pipeline.step3_batchprocess import (
    main as batch_test_main,
)

# Data validation modules
from python.validation.compare_rpeak_bpm_physionet import main as compare_data_main

# Output dir
from python.pre_recorded_testing_pipeline.config import get_output_dir


# === Path to your streaming script ===
STREAM_SCRIPT_BLE = os.path.join(os.path.dirname(__file__), "step4_stream_ble.py")
STREAM_SCRIPT_USB = os.path.join(
    os.path.dirname(__file__), "step4_stream_usb.py"
)  # MUST RENAME THIS FILE
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
datasets_dir = os.path.join(project_root, "datasets")
print(datasets_dir)

# patient_id = "P00001"
# segment_id = "s05"

# file_id_total = patient_id.lower() + "_" + segment_id
# CHANGE THIS LINE TO CHANGE FILE


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


def collect_user_input_test_file():
    while True:
        patient_id = (
            input(
                "What is the Patient ID you would like to test? ID should be entered in the format of P#####: "
            )
            .strip()
            .upper()
        )

        # Check if patient folder exists
        patient_folder = os.path.join(
            datasets_dir, "PhysioNet Datasets", f"ECG_Data_{patient_id}"
        )
        if os.path.exists(patient_folder):
            print(f"Patient folder found: {patient_id}")
            break
        else:
            print(
                f"Patient folder not found for {patient_id}. Please enter a valid Patient ID."
            )

    while True:
        segment_id = (
            input(
                "What is the Segment ID you would like to test? ID should be entered in the format of S##: "
            )
            .strip()
            .lower()
        )

        # Check if segment folder exists within patient folder
        segment_folder = os.path.join(patient_folder, segment_id)
        if os.path.exists(segment_folder):
            print(f"Segment folder found: {segment_id}")
            break
        else:
            print(
                f"Segment folder not found for {segment_id}. Please enter a valid Segment ID."
            )

    return patient_id, segment_id


def run_full_pipeline():

    print("\n🚀 Starting full ECG processing pipeline...\n")

    patient_id, segment_id = collect_user_input_test_file()
    data_transport_method = collect_user_input_USB_BLE()

    file_id_total = patient_id.lower() + "_" + segment_id.lower()
    file_name = os.path.join(
        datasets_dir,
        "PhysioNet Datasets",
        f"ECG_Data_{patient_id}",
        segment_id,
        file_id_total,
    )
    output_dir = get_output_dir(patient_id, segment_id, data_transport_method.upper())
    print(f"✅ Output directory: {output_dir}")
    # === STEP 1: Generate dataset ===
    print("=== STEP 1: Generating ECG dataset ===")
    digital_dataset, r_peaks, num_peaks, inst_bpms = generate_dataset_main(
        file_name=file_name, output_csv_path=output_dir, bit_res=12, start_s=0, end_s=15
    )
    print("✅ Dataset generation complete.\n")

    print("=== STEP 2: Generating firmware file and flashing it to ESP32")
    if data_transport_method == "usb":
        firmware_result = generate_and_flash_firmware_usb(
            digital_dataset=digital_dataset, file_id=file_id_total
        )
    elif data_transport_method == "ble":
        firmware_result = generate_and_flash_firmware_ble(
            digital_dataset=digital_dataset, file_id=file_id_total
        )

    if firmware_result is None:
        print("Firmware flashing failed. Pipeline aborted.")
        return
    print("✅ Firmware flashing complete.\n")

    # === STEP 3: Run batch processing ===
    print("=== STEP 3: Running batch processing ===")
    batch_test_main(
        file_name, output_csv_path=output_dir
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
