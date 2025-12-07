import os, sys

# Add project root to Python path before importing internal packages
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


import sys

# import serial
import time

import matplotlib.pyplot as plt
import numpy as np
import struct
import threading
import json
import wfdb
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import queue
import csv
import datetime
from scipy.signal import butter, sosfilt, sosfilt_zi
import os
from bleak import BleakScanner, BleakClient
import asyncio

# ========= IMPORT CLASSES FROM CORE ===================================================================
from python.core.data_handling import Packet, PacketParser
from python.core.signal_processing import (
    R_peak_detector,
    BPMDetector,
    AD8232_Bandpass_Simulator,
)
from python.core.logging import CSVLogger


class Config:
    def __init__(self, json_path):
        with open(json_path, "r") as f:
            data = json.load(f)

        # Extract parameters from JSON
        self.type_of_data = data.get("type_of_data", "open-source")
        self.open_source_time_s = data.get("open_source_time_s", 5)
        self.bpm = data.get("bpm", 75)
        self.sampling_hz = data.get("sampling_hz", 250)
        self.num_beats = data.get("num_beats", 5)
        self.heartbeat_type = data.get("heartbeat_type", "regular")
        self.durations = data.get("durations", {})
        self.plot_window_s = data.get("plot_window_s", 5)

        # Derived parameters for MCU streaming
        self.fs = self.sampling_hz
        self.packet_size = 28  # ← adjust based on your firmware definition
        self.max_samples_plotted = self.fs * self.plot_window_s  # e.g., 250*5 = 1250


# ========= IMPORT BLE VARIABLE INFORMATION FROM CONFIG ===============================================================================================
from python.tests.ble.ble_config import (
    TARGET_DEVICE_NAME,
    ECG_SERVICE_UUID,
    ECG_DATA_CHARACTERISTIC_UUID,
    ECG_COMMAND_CHARACTERISTIC_UUID,
)

# GLOBAL VARIABLES ====================================================================================

# BLE connection globals
ble_client = None  # Will hold BleakClient when connected
ble_data_queue = queue.Queue()  # Thread-safe queue for BLE data
ble_thread = None  # Will hold the BLE thread reference
last_packet_time = 0  # Track when last BLE data arrived
ble_connection_ready = threading.Event()

# Shared data between threads
received_samples_full = []
received_samples_plot = []
timestamps_full = []
timestamps_plot = []
mcu_timestamps = []

global_sample_counter = 0
current_bpm = 0.0
instantaneous_bpm = 0.0
total_peaks_detected = 0
peak_indices = []
timestamp_errors = []  # Track timestamp vs sample index discrepancies
peak_timestamp_errors = []  # Track errors specifically at peaks

data_lock = threading.Lock()  # Protect received_samples
bpm_lock = threading.Lock()
stop_flag = threading.Event()
# Ensure stop_flag starts cleared
if stop_flag.is_set():
    stop_flag.clear()

# PyQtGraph globals (will be initialized in main)
plot_widget = None
curve = None
status_label = None

# ========================================================================================================================


async def find_and_connect():
    """
    Find and connect to ESP32.
    Mirrors logic from test_ble_streaming.py

    Returns:
        BleakClient: Connected client, or None if failed
    """
    # Scan for device, timeout after 10 seconds
    print(f"Scanning for '{TARGET_DEVICE_NAME}'...")
    device = await BleakScanner.find_device_by_name(TARGET_DEVICE_NAME, timeout=10.0)

    # if device not found, return after timeout
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


async def ble_async_main():
    """
    Async function that runs in BLE thread.
    Mirrors the structure from test_stream_mode() in test_ble_streaming.py
    """
    global ble_client

    # Step 1: Connect to ESP32 (matches test_ble_streaming.py:210-215)
    print("[1/4] Connecting to ESP32...")
    client = (
        await find_and_connect()
    )  # await suspends execution of this function until find_and_connect() has been executed

    if client is None:
        print("ERROR: Failed to connect to BLE device")
        ble_connection_ready.set()  # this releases the lock so that the threads waiting can then start/continue
        return  # Exit if connection failed

    ble_client = client  # Store in global for access from other functions

    try:
        # Step 2: Subscribe to notifications (matches test_ble_streaming.py:218-221)
        print("[2/4] Subscribing to notifications and sending START_STREAM...")
        await client.start_notify(
            ECG_DATA_CHARACTERISTIC_UUID, ble_notification_handler
        )
        await client.write_gatt_char(ECG_COMMAND_CHARACTERISTIC_UUID, b"START")
        print("✓ Streaming started")
        ble_connection_ready.set()

        # Step 3: Keep connection alive until stop_flag is set
        print("[3/4] Streaming data (press STOP to end)...")
        while not stop_flag.is_set():
            await asyncio.sleep(0.1)

        # Step 4: Cleanup - send STOP and disconnect (matches test_ble_streaming.py:232-233)
        print("[4/4] Stopping stream...")
        try:
            if client.is_connected:
                await client.write_gatt_char(ECG_COMMAND_CHARACTERISTIC_UUID, b"STOP")
                await client.stop_notify(ECG_DATA_CHARACTERISTIC_UUID)
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")

    except Exception as e:
        print(f"BLE streaming error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Disconnect (matches test_ble_streaming.py:343-346)
        try:
            if client.is_connected:
                await client.disconnect()
                print("✓ Disconnected from ESP32")
        except Exception as e:
            print(f"Warning: Error during disconnect: {e}")


def ble_thread_func():
    """
    Wrapper function that runs asyncio event loop in BLE thread.
    This is what gets passed to threading.Thread()
    """
    try:
        asyncio.run(ble_async_main())
    except Exception as e:
        print(f"BLE thread error: {e}")
        import traceback

        traceback.print_exc()


def ble_notification_handler(sender, data):
    """
    Called by Bleak when BLE notification received from ESP32.
    Runs in BLE thread context.

    Args:
        sender: BLE characteristic handle (provided by Bleak)
        data: Raw bytes from ESP32
    """
    global last_packet_time

    # Put raw bytes into thread-safe queue
    ble_data_queue.put(data)

    # Update timestamp to track when last data arrived
    last_packet_time = time.time()


# THREAD 1
def read_from_mcu(
    config, csv_logger, bpm_logger, detector, bpm_detector, bandpass_filter
):  # , expected_packet_num, timeout
    global global_sample_counter, current_bpm, instantaneous_bpm, total_peaks_detected, mcu_timestamps, last_packet_time

    parser = PacketParser(config.packet_size)
    print("Listening for packets...\n")

    packet_count = 0

    last_bpm_calculation = time.time()
    start_time = 0
    while not stop_flag.is_set():  # while stop != true, aka while "going"
        # add bytes from the BLE buffer to the buffer array - NEW
        try:
            data = ble_data_queue.get(timeout=0.01)  # 10ms timeout
            parser.update_buffer(data)
        except queue.Empty:
            # No data available - check for timeout
            if time.time() - last_packet_time > 2.0:
                print(
                    f"No data for 2 seconds, assuming done. Received {packet_count} packets"
                )
                break
            time.sleep(0.001)  # Small sleep
            continue  # Skip rest of loop if no data
        # Check how many bytes have arrived from the MCU
        if b"RESET_REASON" in parser.buffer:
            print(f"⚠️ ESP32 RESET DETECTED: {data}")
        if b"BOOT_TIME" in parser.buffer:
            print(f"⚠️ ESP32 RESTARTED: {data}")

        while (
            len(parser.buffer) >= config.packet_size
        ):  # when bytes in buffer > packet size (18 for 8-bit)
            packet = (
                parser.get_packet()
            )  # unpacks packet and assigns values to individual Parser attributes
            if packet is None:
                continue
            parser.packet_count += 1
            mcu_timestamps.append(packet.timestamp)  # in ms for now
            # Check header

            # print(f"Packet ID: {packet.packet_id}, Packet Count: {parser.packet_count}, Timestamp: {packet.timestamp}, Samples: {packet.samples}")

            if parser.packet_count == 1:
                csv_logger.start_time = datetime.datetime.now().isoformat()
                t0_mcu = packet.sample_times[0]

            for i in range(
                len(packet.samples)
            ):  # iterate through samples of each packet
                sample_value = packet.samples[i]
                sample_time = packet.sample_times[i]

                # Track peaks before processing
                peaks_before = len(detector.detected_peaks)

                # if bandpass_filter.apply == True:
                #     sample_value = bandpass_filter.filter_sample(sample_value)
                # Feed sample to R-peak detector
                detector.process_sample(
                    sample_value
                )  # currently processing UNFILTERED VALUES

                # Check if new peak detected
                peaks_after = len(detector.detected_peaks)
                is_peak = (
                    peaks_after > peaks_before
                )  # compare length of peak history before and after detector.process_sample(sample_value)

                if is_peak:
                    peak_sample_index = detector.detected_peaks[
                        -1
                    ]  # if peak detected, find index of peak from last value of detector.detected_peaks

                    bpm_detector.add_peak(
                        peak_sample_index, sample_time
                    )  # append new peak information to bpm_detector

                    with (
                        bpm_lock
                    ):  # this is locked to keep the GUI plot thread from accessing these values for graphing before they are fully updated
                        instantaneous_bpm = bpm_detector.instantaneous_bpm  #
                        total_peaks_detected = len(detector.detected_peaks)

                    with data_lock:
                        peak_indices.append(
                            detector.detected_peaks[-1]
                        )  # global_sample_counter

                    print(
                        f"💓 Peak detected at sample {peak_sample_index} (global: {global_sample_counter}) | Instant BPM: {instantaneous_bpm:.1f}"
                    )
                    bpm_logger.log(
                        peak_sample_index, sample_value, round(instantaneous_bpm, 1)
                    )

                csv_logger.log(
                    packet.sample_times[i],
                    packet.samples[i],
                    packet.packet_id,
                    parser.packet_count,
                )
                # if global_sample_counter % 1000 == 0:
                #     print(f"DEBUG: csv_queue size = {csv_logger.csv_queue.qsize()}")
                global_sample_counter += 1
            with data_lock:
                received_samples_full.extend(packet.samples)
                received_samples_plot.extend(packet.samples)
                timestamps_full.extend(packet.sample_times)
                timestamps_plot.extend(packet.sample_times)

                if len(received_samples_plot) > config.max_samples_plotted:
                    received_samples_plot[:] = received_samples_plot[
                        -config.max_samples_plotted :
                    ]
                    timestamps_plot[:] = timestamps_plot[-config.max_samples_plotted :]

            current_time = time.time()
            if current_time - last_bpm_calculation >= 1.0:
                windowed_bpm = bpm_detector.calculate_bpm_in_window(
                    packet.sample_times[-1]
                )
                with bpm_lock:
                    current_bpm = windowed_bpm
                last_bpm_calculation = current_time

                # PRINT BPM TO CONSOLE
                print(f"📊 Windowed BPM (5s avg): {current_bpm:.1f} BPM")

    print(f"Exited read loop. stop_flag={stop_flag}, packet_count={packet_count}")
    # print("Full set of values: ")
    # print(received_samples_full)
    print("Full set of BPM: ")
    print(bpm_detector.bpm_history)

    # mcu_timestamp_diff can be checked to ensure no timestamp drift
    mcu_timestamp_diff = [
        mcu_timestamps[i + 1] - mcu_timestamps[i]
        for i in range(len(mcu_timestamps) - 1)
    ]
    # print(mcu_timestamp_diff)
    print("Detected R-peaks (sample indices):", detector.detected_peaks)


def keyboard_listener():
    while True:
        cmd = input("Type STOP to halt data stream: ").strip().upper()
        if cmd == "STOP":
            stop_flag.set()
            print("Stop flag set.")
            break


def thread_stop_command():
    listen_for_stop_thread = threading.Thread(target=keyboard_listener, daemon=True)
    listen_for_stop_thread.start()


# NEW FUNCTION - UPDATE PLOT
def update_plot():
    """Called by Qt timer: Updates the real-time plot"""
    global curve, status_label

    # Thread-safe: Lock when reading shared data
    with data_lock:
        x = np.array(timestamps_plot)
        y = np.array(received_samples_plot)

        # data_copy = received_samples_plot.copy()
        total_received = len(received_samples_full)

        if len(x) > 0:
            curve.setData(x, y)
            status_label.setText(f"Total samples received: {total_received}")
        else:
            curve.clear()
            status_label.setText("Waiting for data...")


def start_streaming_from_mcu(
    config, csv_logger, bpm_logger, detector, bpm_detector, bandpass_filter
):
    global global_sample_counter, timestamp_errors, peak_timestamp_errors, last_packet_time, ble_thread
    # Initialize to future time to give ESP32 time for 3-second startup delay
    last_packet_time = time.time() + 5.0  # Add 5 seconds buffer

    with data_lock:
        received_samples_full.clear()  # clear array of all received samples
        received_samples_plot.clear()  # clear array of plotted samples
        timestamps_full.clear()  # clear array of all timestamps
        timestamps_plot.clear()  # clear array of plotted timestamps
        peak_indices.clear()  # clear array of peak indices
    # stop_flag.clear() #reset stop flag to false, so thread is running
    # ser.reset_input_buffer() #clear bytes in cue to be read from MCU
    # ser.reset_output_buffer() #clear bytes in cue to be sent to MCU

    with bpm_lock:  #
        global current_bpm, instantaneous_bpm, total_peaks_detected
        current_bpm = 0.0
        instantaneous_bpm = 0.0
        total_peaks_detected = 0

    global_sample_counter = 0  # Reset counter

    detector.__init__(
        fs=config.fs, sec_of_calibration=2, slope_spacing=4, mov_ave_window=15
    )
    bpm_detector.__init__(fs=config.fs, window_of_averaging=5)

    # Clear BLE queue
    while not ble_data_queue.empty():
        ble_data_queue.get()

    # Start BLE connection in background thread
    print("Starting BLE connection thread...")
    ble_thread = threading.Thread(target=ble_thread_func, daemon=True)
    ble_thread.start()

    # Wait for BLE connection to complete (with timeout)
    print("Waiting for BLE connection...")
    if not ble_connection_ready.wait(timeout=15.0):  # ← Wait up to 15 seconds
        print("ERROR: BLE connection timeout")
        return  # Don't start processing thread
    # Only start processing if BLE connected successfully
    if ble_client is None:
        print("ERROR: BLE client not connected")
        return

    print("BLE connected, starting data processing thread...")

    mcu_read_thread = threading.Thread(
        target=read_from_mcu,
        args=(config, csv_logger, bpm_logger, detector, bpm_detector, bandpass_filter),
        daemon=True,
    )
    mcu_read_thread.start()


def stop_streaming_from_mcu():
    """
    Stop BLE streaming by setting stop flag.
    The BLE thread (ble_async_main) will detect this and send STOP_STREAM command.
    """
    stop_flag.set()
    time.sleep(0.5)  # Give BLE thread time to send STOP and disconnect
    stop_flag.clear()


def main(output_csv_path=None):

    # Create default folder if output_csv_path = empty
    if len(sys.argv) > 1:
        output_csv_path = sys.argv[1]
    elif output_csv_path is None:
        output_csv_path = os.path.join(os.getcwd(), "data_logs/default_run")

    global plot_widget, curve, status_label  # global variables that will update over course of run

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    config_path = os.path.join(project_root, "heartrate_config.json")
    config = Config(config_path)

    # Use shared data_logs path from master controller
    os.makedirs(output_csv_path, exist_ok=True)

    raw_csv_path = os.path.join(output_csv_path, "streamed_raw_packets.csv")
    bpm_csv_path = os.path.join(output_csv_path, "streamed_data_outputs.csv")

    # Clear stop flag BEFORE creating CSV loggers
    stop_flag.clear()

    with data_lock:
        received_samples_full.clear()
        received_samples_plot.clear()
        timestamps_full.clear()
        timestamps_plot.clear()

    csv_logger = CSVLogger(raw_csv_path, stop_flag)
    csv_logger.create_CSV(header=["Time", "Sample", "Packet ID", "Packet Count"])

    bpm_logger = CSVLogger(bpm_csv_path, stop_flag)
    bpm_logger.create_CSV(
        header=["Detected R_peak_index", "Digital Value", "Instantaneous_BPM"]
    )

    detector = R_peak_detector(
        fs=config.fs, sec_of_calibration=2, slope_spacing=4, mov_ave_window=15
    )
    bpm_detector = BPMDetector(fs=config.fs, window_of_averaging=5)
    bandpass_filter = AD8232_Bandpass_Simulator(
        fs=config.fs, hp_cutoff=0.5, lp_cutoff=25, order=2
    )

    """Is this all necessary?"""
    # Create Qt application
    app = QtWidgets.QApplication(sys.argv)

    # Create main window
    win = QtWidgets.QMainWindow()
    win.setWindowTitle("Real-Time ECG Monitor")
    win.setGeometry(100, 100, 1200, 600)

    # Create central widget and layout
    central_widget = QtWidgets.QWidget()
    win.setCentralWidget(central_widget)
    layout = QtWidgets.QVBoxLayout(central_widget)
    """"""

    # Create plot widget
    plot_widget = pg.PlotWidget()
    plot_widget.setLabel("left", "ADC Value")
    plot_widget.setLabel("bottom", "Time (s)")
    plot_widget.setTitle("Real-Time ECG Signal")
    plot_widget.showGrid(x=True, y=True)
    plot_widget.setYRange(1300, 2500)  # 12-bit ADC range
    ax = plot_widget.getAxis("bottom")
    ax.setTickSpacing(major=1.0, minor=0.5)  # 1 s major, 0.5 s minor

    # Create plot line
    curve = plot_widget.plot(pen=pg.mkPen(color="#00FF00", width=2))  # Green line

    # Create status label
    status_label = QtWidgets.QLabel(
        f"Status: Ready to receive data "
    )  # (expecting {expected_packet_num} packets)")

    # Add widgets to layout
    layout.addWidget(plot_widget)
    layout.addWidget(status_label)

    def on_window_close(event):
        print("Window is closing! Stopping threads...")
        stop_flag.set()  # Tell all threads to stop

        # Give BLE thread time to send STOP command and disconnect
        print("Waiting for BLE thread to stop...")
        time.sleep(2.0)

        # Wait for the logger threads to finish their final writes (raw data and R-peak/BPM)
        print("Flushing CSV logs...")
        if csv_logger._thread:
            csv_logger._thread.join(timeout=3.0)
        if bpm_logger._thread:
            bpm_logger._thread.join(timeout=3.0)

        print(f"✓ Raw data saved to: {raw_csv_path}")
        print(f"✓ BPM data saved to: {bpm_csv_path}")

        event.accept()  # Allow the window to close

    win.closeEvent = on_window_close
    # Setup timer to update plot periodically
    timer = QtCore.QTimer()
    timer.timeout.connect(update_plot)
    timer.start(200)  # Update every 80ms (20 FPS)

    def start_everything():

        start_streaming_from_mcu(
            config, csv_logger, bpm_logger, detector, bpm_detector, bandpass_filter
        )
        thread_stop_command()

    # Start streaming in background (after small delay for GUI to load)
    QtCore.QTimer.singleShot(500, start_everything)
    # Show window
    win.show()

    # Run Qt application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
