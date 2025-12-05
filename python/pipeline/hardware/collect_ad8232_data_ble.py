"""
Python script to receive streamed AD8232 data from ESP32 via BLE.

How to Use:
Change the file name variables as needed to reflect testing condition. Make sure to maintain unique file names for every new testing condition.
Specify duration of recording in seconds.
Make sure that the correct firmware file (stream_ad8232_data_ble.ino) has been flashed to the MCU.
Run the file. When the recording session is complete, a graph will be generated of the collected data.
Review the graph - if the data looks acceptable, enter "Y" into the terminal to save it to the specified file path. If not, enter "N" (this will discard the dataset).
"""

import matplotlib.pyplot as plt
import os
import csv
import time
import struct
import asyncio
from bleak import BleakScanner, BleakClient

# Import BLE configuration (UUIDs and device name)
from python.tests.ble.ble_config import (
    TARGET_DEVICE_NAME,
    ECG_SERVICE_UUID,
    ECG_DATA_CHARACTERISTIC_UUID,
    ECG_COMMAND_CHARACTERISTIC_UUID,
)

# Configuration
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

# Global variable to collect samples from BLE notifications
collected_samples = []


async def find_and_connect():
    """
    Find and connect to ESP32 via BLE.

    Returns:
        BleakClient: Connected client, or None if failed
    """
    # Scan for device, timeout after 10 seconds
    print(f"Scanning for '{TARGET_DEVICE_NAME}'...")
    device = await BleakScanner.find_device_by_name(TARGET_DEVICE_NAME, timeout=10.0)

    if device is None:
        print(f"ERROR: '{TARGET_DEVICE_NAME}' not found")
        return None

    print(f"Found '{TARGET_DEVICE_NAME}' at {device.address}")

    # Connect
    client = BleakClient(device.address)
    await client.connect()

    if client.is_connected:
        print("Connected successfully")
        return client
    else:
        print("Connection failed")
        return None


def notification_handler(sender, data):
    """
    Called by Bleak when BLE notification received from ESP32.

    Args:
        sender: BLE characteristic handle (provided by Bleak)
        data: Raw bytes from ESP32 (500 bytes = 250 uint16_t samples)
        * data will be sent every 250 samples (1 second) - this is configured in the firmware file *

    """
    global collected_samples

    # Unpack binary data: 250 uint16_t values (little-endian)
    # '<' = little-endian, 'H' = unsigned short (uint16_t), '250H' = 250 values
    samples = struct.unpack("<250H", data)
    collected_samples.extend(samples)

    # Print progress
    elapsed_seconds = len(collected_samples) / SAMPLING_RATE
    print(
        f"Received {len(samples)} samples (total: {len(collected_samples)} = {elapsed_seconds:.1f}s)"
    )


async def main():
    """Main function to collect ECG data via BLE"""
    global collected_samples

    # Connect to ESP32 via BLE
    print("Connecting to ESP32...")
    client = await find_and_connect()

    if client is None:
        print("ERROR: Failed to connect to ESP32")
        return None

    try:
        # Clear collected samples
        collected_samples = []

        # Subscribe to notifications
        print("Subscribing to data notifications...")
        await client.start_notify(ECG_DATA_CHARACTERISTIC_UUID, notification_handler)

        # Send START command
        print("Sending START command...")
        await client.write_gatt_char(ECG_COMMAND_CHARACTERISTIC_UUID, b"START")

        # Collect streaming data
        print("Collecting data...")
        start_time = time.time()

        # Wait until all samples are collected (measuring by sample number, not time)
        while len(collected_samples) < TARGET_SAMPLES:
            await asyncio.sleep(0.1)  # Check every 100ms

            # Safety timeout (1.5x expected duration)
            if time.time() - start_time > DURATION_SEC * 1.5:
                print(
                    f"\nTimeout - Only received {len(collected_samples)} samples after {DURATION_SEC * 1.5} seconds."
                )
                print(
                    f"\nExpected {TARGET_SAMPLES} samples in {DURATION_SEC} seconds. "
                )
                break

        # Send STOP command
        print(f"\nReached target of {TARGET_SAMPLES} samples.")
        await client.write_gatt_char(ECG_COMMAND_CHARACTERISTIC_UUID, b"STOP")

        # Stop notifications
        await client.stop_notify(ECG_DATA_CHARACTERISTIC_UUID)

    finally:
        # Disconnect
        if client.is_connected:
            await client.disconnect()
            print("Disconnected from ESP32")

    # Use collected samples as ad8232_recorded_data
    ad8232_recorded_data = collected_samples[:TARGET_SAMPLES]  # Trim to exact target

    if len(ad8232_recorded_data) < TARGET_SAMPLES:
        print("Incomplete recording.")
    elif len(collected_samples) > TARGET_SAMPLES:
        print(
            f"Excess samples recorded ({len(collected_samples)}), trimmed to {TARGET_SAMPLES}"
        )
    else:
        now = time.time()
        print("Target number of samples recorded!")
        print(f"Total time taken = {now - start_time:.1f} seconds.")

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

    # Plot data
    plt.figure(figsize=(12, 6))
    plt.plot(ad8232_recorded_data)
    plt.title("AD8232 ECG Data (BLE-streamed)")
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
        plt.title("AD8232 ECG Data (BLE-streamed)")
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
        print(f"   python python/pipeline/master_controller_ad8232_ble.py")
        return data_file_name

    else:
        print("❌ Dataset discarded. Run again to collect new data.")
        return None


if __name__ == "__main__":
    asyncio.run(main())
