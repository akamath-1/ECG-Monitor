import os
import subprocess
import time
from datetime import datetime

# === Import local modules ===
from python.pipeline.step1_generate_dataset_physionet import main as generate_dataset_main
from python.pipeline.step2_flash_firmware import main as generate_and_flash_firmware
from python.pipeline.step3_batchprocess import main as batch_test_main
from python.validation.compare_rpeak_bpm_physionet import main as compare_data_main
from python.pipeline.config import get_output_dir

# === Path to your streaming script ===
STREAM_SCRIPT = os.path.join(os.path.dirname(__file__), "step4_stream.py")
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
datasets_dir = os.path.join(project_root, "datasets")
print(datasets_dir)

patient_id = "P00001"
segment_id = "s05"
file_id_total = patient_id.lower() + "_" + segment_id
file_name = os.path.join(
    datasets_dir,
    "PhysioNet Datasets",
    f"ECG_Data_{patient_id}",
    segment_id,
    file_id_total,
)  # CHANGE THIS LINE TO CHANGE FILE

output_dir = get_output_dir(patient_id, segment_id)

print(f"✅ Output directory: {output_dir}")


def run_full_pipeline():

    print("\n🚀 Starting full ECG processing pipeline...\n")

    # === STEP 1: Generate dataset ===
    print("=== STEP 1: Generating ECG dataset ===")
    digital_dataset, r_peaks, num_peaks, inst_bpms = generate_dataset_main(
        file_name=file_name, output_csv_path=output_dir, bit_res=12, start_s=0, end_s=15
    )
    print("✅ Dataset generation complete.\n")

    print("=== STEP 2: Generating firmware file and flashing it to ESP32")
    generate_and_flash_firmware(digital_dataset=digital_dataset, file_id=file_id_total)
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
    subprocess.run(
        ["python3", STREAM_SCRIPT, output_dir], cwd=project_root
    )  # add project_root to make sure it is running from project root, not working directory
    print("✅ Streaming complete.\n")

    # # === STEP 5: Graph and compare ===
    # print("=== STEP 5: Generating comparison graphs ===")
    # compare_data_main(csv_logs_folder_path=output_dir)
    # print("✅ Graph generation complete.\n")

    # print("🎯 Full ECG pipeline completed successfully!")


if __name__ == "__main__":

    run_full_pipeline()
