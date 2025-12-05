"""
Python script to receive streamed AD8232 data from ESP32 via USB.

How to Use:
Change the file name variables as needed to reflect testing condition. Make sure to maintain unique file names for every new testing condition.
Specify duration of recording in seconds.
Make sure that the correct firmware file (stream_ad8232_data_usb.ino) has been flashed to the MCU.
Run the file. When the recording session is complete, a graph will be generated of the collected data.
Review the graph - if the data looks acceptable, enter "Y" into the terminal to save it to the specified file path. If not, enter "N" (this will discard the dataset).
"""

import matplotlib.pyplot as plt
import serial.tools.list_ports
import os
import csv

"""
Simple ECG Data Collector
Sends START command to ESP32 and collects streaming data into array
"""

import serial
import time


def detect_port():
    ports = serial.tools.list_ports.comports()
    # ports.name = cu.usbserial-0001
    # ports.device = /dev/cu.usbserial-0001
    # ports.description = CP2102 USB to UART Bridge Controller
    keywords_description = ["usb", "serial", "ch340", "cp210", "ftdi"]
    for p in ports:
        if "usbserial" in p.device or any(
            keyword in p.description.lower() for keyword in keywords_description
        ):
            print(f"Found port: {p.device}")
            return p.device
    print("Error: Port not found.")
    return None


# Configuration
PORT = detect_port()
print(PORT)
BAUDRATE = 115200
TIMEOUT = 2
BASELINE = 1.5
V_MAX = 3.3
ADC_MAX = 4095.0
GAIN = 500

# ============== FILE DESCRIPTION - USER CHANGES THESE ! ===============================
CONDITION = "walk"  # "rest" or "movement", "post_exercise"
RUN_NUMBER = 1
DURATION_SEC = 30
# =============================================================================================

SAMPLING_RATE = 250
TARGET_SAMPLES = DURATION_SEC * SAMPLING_RATE


data_file_name = (
    f"ad8232_{CONDITION}_run{RUN_NUMBER}_{DURATION_SEC}_{SAMPLING_RATE}.csv"
)
output_dir = "datasets/AD8232 Data"
os.makedirs(output_dir, exist_ok=True)
file_path_name = os.path.join(output_dir, data_file_name)


def main():
    # Connect to ESP32
    print("Connecting to ESP32...")
    ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)
    time.sleep(2)  # Wait for ESP32 to reset

    print(f"Connected to {PORT}")

    # Clear any existing data in buffer
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Send START command
    print("Sending START command...")
    ser.write(b"START\n")

    # Array to store data
    ad8232_recorded_data = []

    # Collect streaming data
    print("Collecting data...")

    start_time = time.time()
    while True:
        try:
            # Read line from serial
            line = ser.readline().decode("utf-8").strip()

            if not line:
                continue

            # Check if we got a number
            try:
                value = int(line)
                ad8232_recorded_data.append(value)

                # Print progress every 1000 samples
                if len(ad8232_recorded_data) % 1000 == 0:
                    elapsed = time.time() - start_time
                    print(
                        f"Collected {len(ad8232_recorded_data)} samples in {elapsed:.1f}s"
                    )
                if len(ad8232_recorded_data) >= TARGET_SAMPLES:

                    print(f"\n✅ Reached target of {TARGET_SAMPLES} samples.")
                    ser.write(b"STOP\n")  # Tell MCU to stop
                    break

            except ValueError:
                # Not a number, probably a status message
                print(f"MCU: {line}")

                # Check for end marker
                if "COMPLETE" in line or "END" in line:
                    print("Collection complete!")
                    break

        except KeyboardInterrupt:
            print("\nStopped by user")
            break

        except Exception as e:
            print(f"Error: {e}")
            break

    # Close serial connection
    ser.close()

    if len(ad8232_recorded_data) < TARGET_SAMPLES:
        print("Incomplete recording.")
    elif len(ad8232_recorded_data) > TARGET_SAMPLES:
        print("Excess samples recorded.")
    else:
        print("Target number of samples recorded!")
    # CONVERT DIGITAL DATA TO BIASED VOLTAGE AND RAW VOLTAGE:

    voltages_biased = [
        (val / ADC_MAX) * V_MAX for val in ad8232_recorded_data
    ]  # divide by ADC max (4095 for 12bit) and multiple by Vmax for analog distribution from 0-Vmax volts - biased voltages
    voltages_amplified = [
        val - BASELINE for val in voltages_biased
    ]  # subtract baseline to get amplified voltages
    voltages_raw_mV = [
        (val * 1000) / GAIN for val in voltages_amplified
    ]  # multiply by 1000 for V --> mV, divide my gain to de-amplify signal (this is raw signal)

    # Print results
    print(f"\nTotal samples collected: {len(ad8232_recorded_data)}")
    print(f"First 10 values: {ad8232_recorded_data[:10]}")
    print(f"Last 10 values: {ad8232_recorded_data[-10:]}")

    # Save to file (optional)
    with open(file_path_name, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Raw_mV", "Biased_V"])
        for i in range(len(ad8232_recorded_data)):
            writer.writerow(
                [round(voltages_raw_mV[i], 3), round(voltages_biased[i], 3)]
            )

    print(f"Data saved to {file_path_name}.")

    # Plot data
    plt.figure(figsize=(12, 6))
    plt.plot(ad8232_recorded_data)
    plt.title("AD8232 ECG Data (USB-streamed)")
    plt.xlabel("Sample")
    plt.ylabel("ADC Value")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

    print("\n" + "=" * 60)
    response = (
        input(
            "Please inspect the generated graph of the collected data. Would you like to save this dataset? (Y/N): "
        )
        .strip()
        .lower()
    )

    if response == "y":
        # Save CSV file
        with open(file_path_name, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["Raw_mV", "Biased_V"])
            for i in range(len(ad8232_recorded_data)):
                writer.writerow(
                    [round(voltages_raw_mV[i], 3), round(voltages_biased[i], 3)]
                )

        # Save graph image
        graph_file_name = data_file_name.replace(".csv", "_graph.png")
        graph_file_path = os.path.join(output_dir, graph_file_name)

        plt.figure(figsize=(12, 6))
        plt.plot(ad8232_recorded_data)
        plt.title("AD8232 ECG Data (USB-streamed)")
        plt.xlabel("Sample")
        plt.ylabel("ADC Value")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(graph_file_path, dpi=300, bbox_inches="tight")
        plt.close()  # Close the figure to free memory

        print(f"✅ Data saved to {file_path_name}")
        print(f"✅ Graph saved to {graph_file_path}")
        print(f"   Filename: {data_file_name}")
        print("\nYou can now run the processing pipeline:")
        print(f"   python python/pipeline/master_controller_ad8232_usb.py")
        return data_file_name

    else:
        print("❌ Dataset discarded. Run again to collect new data.")
        return None


if __name__ == "__main__":
    main()
