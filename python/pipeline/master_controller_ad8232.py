import os
import subprocess
import time
from datetime import datetime

# === Import local modules ===

from python.pipeline.step1_generate_dataset_ad8232 import (
    main as generate_dataset_ad8232_main,
)
from python.pipeline.step2_flash_firmware import main as generate_and_flash_firmware
from python.pipeline.step3_batchprocess import main as batch_test_main
from python.validation.compare_rpeak_bpm_ad8232 import (
    main as compare_ad8232_data_main,
)
from python.pipeline.config import get_output_dir

# FILE DESCRIPTION
CONDITION = "rest"  # or "movement", "post_exercise"
RUN_NUMBER = 2
DURATION_SEC = 30
SAMPLING_RATE = 250
TARGET_SAMPLES = DURATION_SEC * SAMPLING_RATE
data_file_name_base = (
    f"ad8232_{CONDITION}_run{RUN_NUMBER}_{DURATION_SEC}_{SAMPLING_RATE}"
)

# === PATHS =============================
STREAM_SCRIPT = os.path.join(os.path.dirname(__file__), "step4_stream.py")
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


# OUTPUT DIRECTORY FOR THIS RUN:
output_dir = os.path.join(project_root, "data_logs", "AD8232", data_file_name_base)
os.makedirs(output_dir, exist_ok=True)

print(f"Output directory for data logs: {output_dir}")


def run_full_pipeline():

    print("\n🚀 Starting full AD8232 ECG processing pipeline...\n")
    print(f"   Condition: {CONDITION}")
    print(f"   Run: {RUN_NUMBER}")
    print(f"   Duration: {DURATION_SEC}s at {SAMPLING_RATE}Hz\n")

    # Verify input file exists
    input_csv = f"{data_file_name_base}.csv"
    input_path = os.path.join(project_root, "datasets", "AD8232 Datasets", input_csv)

    if not os.path.exists(input_path):
        print(f"❌ Error: Input file not found: {input_path}")
        print(f"\nPlease run data collection first:")
        print(f"   python python/pipeline/hardware/collect_ad8232_data.py")
        return

    # === STEP 1: Converting data to digital form ===

    # ADD SOMETHING HERE THAT ALLOWS USER TO ACCEPT OR REJECT COLLECTED DATASET AND TRY AGAIN OR QUIT
    print("=== STEP 1: Converting ECG data to digital form ===")
    digital_dataset = generate_dataset_ad8232_main(input_csv)
    print("Digital dataset successfully generated.")

    print("=== STEP 2: Generating firmware file and flashing it to ESP32")
    result_flash = generate_and_flash_firmware(
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
    subprocess.run(
        ["python3", STREAM_SCRIPT, output_dir], cwd=project_root
    )  # add project_root to make sure it is running from project root, not working directory
    print("✅ Streaming complete.\n")

    # === STEP 5: Graph and compare ===
    print("=== STEP 5: Generating comparison graphs ===")
    compare_ad8232_data_main(csv_logs_folder_path=output_dir)
    print("✅ Graph generation complete.\n")

    print("🎯 Full ECG pipeline completed successfully!")


if __name__ == "__main__":

    run_full_pipeline()
