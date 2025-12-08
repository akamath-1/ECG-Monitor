import os
import subprocess
import time
from datetime import datetime

# * NOTE * This pipeline ONLY has provision for streaming data from the AD8232-ESP32 module to the host device via BLE (unlike pre-recording testing pipeline, which can use
# both USB and BLE).
# Use of BLE allows for flexibility for the user to move freely during data acquisition and reduce unnecessary chord strain/pulling.

# Sampling rate is currently fixed at 250hz. Future updates can be added to make this user-modifiable.

# === Import local modules ===


from python.real_time_testing_pipeline.step1_flash_firmware_realtime import (
    main as generate_and_flash_firmware,
)
from python.real_time_testing_pipeline.step3_batchprocess_ecg_realtime import (
    main as batch_test_main,
)
from python.validation.compare_rpeak_bpm_ad8232_livestreamed import (
    main as compare_ad8232_data_main_livestreamed,
)
from python.real_time_testing_pipeline.config import get_output_dir

# SAMPLING RATE HARD-CODED FOR NOW - CAN BE CHANGED TO BE USER-DETERMINED LATER
SAMPLING_RATE = 250


# === PATHS =============================
STREAM_SCRIPT = os.path.join(os.path.dirname(__file__), "step2_stream_ble_realtime.py")
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


# OUTPUT DIRECTORY FOR THIS RUN:
output_dir = os.path.join(
    project_root, "data_logs", "ECG Real-Time", data_file_name_base
)
os.makedirs(output_dir, exist_ok=True)

print(f"Output directory for data logs: {output_dir}")


def collect_user_inputs():

    # Collect and validate user inputs for file name and testing duration.
    # Returns:(file_name, duration_sec, data_file_name_base, output_dir)

    # Collect and validate file name
    while True:
        user_dictated_file_name = (
            input(
                "Please enter the file name you would like to assign to this dataset.\n"
                "Enter a name that is representative of the testing condition and easily identifiable.\n"
                'Use only letters and numbers in the name, and connect all words with "_". (ex: walking_run1): '
            )
            .strip()
            .lower()
        )

        # Check if file name is empty
        if not user_dictated_file_name:
            print("File name cannot be empty. Please try again.\n")
            continue

        # Check if file name contains only valid characters (alphanumeric and underscores)
        if not all(c.isalnum() or c == "_" for c in user_dictated_file_name):
            print(
                "File name can only contain letters, numbers, and underscores (_). Please try again.\n"
            )
            continue

        # Check if file name starts with a letter or number (not underscore)
        if user_dictated_file_name[0] == "_":
            print("File name cannot start with an underscore. Please try again.\n")
            continue

        print(f"File name '{user_dictated_file_name}' is valid.\n")
        break

    # Collect and validate duration
    while True:
        user_dictated_duration_input = input(
            "Enter the time in seconds for recording duration (between 10 and 120): "
        ).strip()

        # Check if input is a valid integer
        try:
            user_dictated_duration = int(user_dictated_duration_input)
        except ValueError:
            print(
                "Invalid input. Please enter a whole number (integer) between 10 and 120.\n"
            )
            continue

        # Check if duration is within valid range
        if user_dictated_duration < 10 or user_dictated_duration > 120:
            print(
                f"Duration must be between 10 and 120 seconds. You entered: {user_dictated_duration}\n"
            )
            continue

        print(f"Duration set to {user_dictated_duration} seconds.\n")
        break

    # Build file path and validate it
    data_file_name_base = (
        f"ad8232_{user_dictated_file_name}_{user_dictated_duration}s_{SAMPLING_RATE}hz"
    )
    output_dir_temp = os.path.join(
        project_root, "data_logs", "ECG Real-Time", data_file_name_base
    )
    csv_file_path = os.path.join(output_dir_temp, "streamed_raw_packets.csv")

    # Check if file already exists
    if os.path.exists(csv_file_path):
        print(f"WARNING: A file with this name already exists:")
        print(f"{csv_file_path}\n")

        while True:
            overwrite_choice = (
                input(
                    "Would you like to:\n"
                    "  [O] Overwrite the existing file?\n"
                    "  [R] Rename and choose a different file name?\n"
                    "Please enter O or R: "
                )
                .strip()
                .upper()
            )

            if overwrite_choice == "O":
                print(f"Existing file will be overwritten.\n")
                break
            elif overwrite_choice == "R":
                print("Returning to file name input...\n")
                # Recursively call this function to start over
                return collect_user_inputs()
            else:
                print("Invalid choice. Please enter O or R.\n")

    return (
        user_dictated_file_name,
        user_dictated_duration,
        data_file_name_base,
        output_dir_temp,
    )


def save_metadata_file(output_dir, file_name, duration_sec, sampling_rate):

    # Create and save a metadata text file with recording information and user notes.
    """
    Args:
        output_dir: Directory where the metadata file will be saved
        file_name: User-provided file name for the dataset
        duration_sec: Recording duration in seconds
        sampling_rate: Sampling rate in Hz
    """
    print("\n=== STEP 5: Saving metadata and notes ===")

    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Collect user notes
    print("\nYou can now add additional notes about this recording.")
    print(
        "Enter your notes below (press Enter twice when finished, or type 'skip' to skip):\n"
    )

    user_notes = []
    skip_notes = False

    while True:
        line = input()
        if line.lower() == "skip":
            skip_notes = True
            break
        if line == "":
            # Check if this is the second consecutive empty line
            if len(user_notes) > 0 and user_notes[-1] == "":
                user_notes.pop()  # Remove the last empty line
                break
        user_notes.append(line)

    # Build metadata content
    metadata_content = f"""ECG RECORDING METADATA
    {'=' * 50}

    Recording Information:
    - File Name: {file_name}
    - Date/Time: {timestamp}
    - Duration: {duration_sec} seconds
    - Sampling Rate: {sampling_rate} Hz
    - Total Expected Samples: {duration_sec * sampling_rate}

    Dataset Details:
    - Sensor: AD8232 ECG Module
    - Microcontroller: ESP32
    - Data Transport: BLE (Bluetooth Low Energy)
    - ADC Resolution: 12-bit (0-4095)

    {'=' * 50}

    User Notes:
    """

    if skip_notes or not user_notes:
        metadata_content += "  (No additional user notes provided)\n"
    else:
        for note_line in user_notes:
            metadata_content += f"  {note_line}\n"

    metadata_content += f"\n{'=' * 50}\n"
    metadata_content += "End of metadata file\n"

    # Save to file
    metadata_file_path = os.path.join(output_dir, "recording_metadata.txt")
    with open(metadata_file_path, "w") as f:
        f.write(metadata_content)

    print(f"\nMetadata saved to: {metadata_file_path}\n")
    return metadata_file_path


def run_full_pipeline():

    print("\n🚀 Starting full AD8232 ECG real-time streaming pipeline...\n")

    # gather all user inputs for data collection and file naming
    user_dictated_file_name, user_dictated_duration, data_file_name_base, output_dir = (
        collect_user_inputs()
    )

    # ask user to whether or not to flash firmware to ESP32 - step can be skipped if firmware is already uploaded to ESP32
    flash_firmware_yn = (
        input("Flash firmware to ESP32? Please enter Y/N: ").strip().lower()
    )

    # change this step to flash a new firmware file to the ESP32
    if flash_firmware_yn == "y":
        print("=== STEP 1: Generating firmware file and flashing it to ESP32")
        result_flash = generate_and_flash_firmware()
        if result_flash == None:
            print("Issue with firmware flashing. Aborting run.")
            return
        print("✅ Firmware flashing complete.\n")
    elif flash_firmware_yn == "n":
        print("STEP 1 (flashing firmware) skipped. Moving on to next step.")
        time.sleep(2)

    # THIS STEP NEEDS TO NOW OUTPUT A CSV WITH THE FULL DATA THAT CAN BE PASSED INTO BATCH PROCESSING
    # === STEP 2: Stream data from MCU ===
    print("=== STEP 2: Running ESP32 streaming ===")
    print(
        f"🧠 Note: This will open the real-time ECG GUI. Recording will automatically stop after {user_dictated_duration} seconds."
    )
    print("You can also close the window or type STOP to end early.")
    time.sleep(2)
    subprocess.run(
        ["python3", STREAM_SCRIPT, output_dir, str(user_dictated_duration)],
        cwd=project_root,
    )  # add project_root to make sure it is running from project root, not working directory
    print("✅ Streaming complete.\n")
    csv_path = os.path.join(output_dir, "streamed_raw_packets.csv")

    # === STEP 3: Run batch processing ===
    print("=== STEP 3: Running batch processing ===")
    batch_test_main(
        csv_file_path=csv_path, output_csv_path=output_dir
    )  # This saves the batch processed outputs
    print("✅ Batch processing complete.\n")

    # === STEP 4: Graph and compare ===
    print("=== STEP 4: Generating comparison graphs ===")
    plot_save_path = os.path.join(output_dir, "comparison_plot.png")
    compare_ad8232_data_main_livestreamed(
        csv_logs_folder_path=output_dir, save_path=plot_save_path
    )
    print("✅ Graph generation complete.\n")

    # === STEP 5: Save metadata and notes ===
    save_metadata_file(
        output_dir=output_dir,
        file_name=user_dictated_file_name,
        duration_sec=user_dictated_duration,
        sampling_rate=SAMPLING_RATE,
    )

    print("✅ Full ECG pipeline completed successfully!")
    print(f"✅ All data saved to: {output_dir}\n")


if __name__ == "__main__":

    run_full_pipeline()
