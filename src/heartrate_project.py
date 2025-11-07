# This version of the code now does the following:
# Real-time ECG streaming and visualization interface for MCU data.
# Streams a generated ECG dataset to the MCU, decodes incoming binary packets, and plots them live using PyQtGraph.
# Displays continuous ECG waveforms, timestamps, and sample counts in a responsive GUI.
# Note: timestamps are artificially generated for now due to timing issues between host device and MCU. Will address this when testing signal generated with hardware. 

import sys
import serial
import time
from src.heartrate_generator import create_dataset
import matplotlib.pyplot as plt
import numpy as np
import struct
import threading
import json
import wfdb
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

ser = serial.Serial('/dev/cu.usbserial-0001', 115200, timeout=1)
time.sleep(2)  # Wait for connection to stabilize

# Clear any leftover data in buffers
ser.reset_input_buffer()
ser.reset_output_buffer()

record = wfdb.rdrecord('ECG_Data_P0000/p00000_s00', sampfrom=0, sampto=250*1)



with open("heartrate_config.json") as f:
    config = json.load(f)

bpm = config["bpm"]
#fs = config["sampling_hz"]
fs = 250
num_beats = 2 #config["num_beats"]
heartbeat_type = config["heartbeat_type"]
durations_json = config["durations"]
packet_size = 28
dataset_type = config["type_of_data"] 
open_source_time_s = config["open_source_time_s"]
received_samples = []
plot_window_s = config["plot_window_s"]

# Shared data between threads
received_samples_full = [] # NEW
received_samples_plot = [] # NEW
timestamps_full = [] # NEW
timestamps_plot = [] # NEW
max_samples_plotted = int(fs * plot_window_s)
data_lock = threading.Lock()  # NEW - Protect received_samples
stop_flag = threading.Event()

# NEW - PyQtGraph globals (will be initialized in main)
plot_widget = None
curve = None
status_label = None

# THREAD 1
def stream(ecg_digital):
    # Send a command to start streaming
    ser.write(b'START\n')
    time.sleep(0.1)
    
    for sample in ecg_digital:
        # Convert sample to bytes (2 bytes for 12-bit ADC)
        ser.write(int(sample).to_bytes(2, byteorder='little'))
        time.sleep(1/fs)  # maintain 500 Hz

# THREAD 2
def read_from_mcu(packet_size): #, expected_packet_num, timeout
    
    print("Listening for packets...\n")
    buffer = b''
    packet_count = 0
    last_packet_time = time.time()
    start_time = 0
    while not stop_flag.is_set():
        #add bytes from the serial port to the buffer array
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            buffer += data
            last_packet_time = time.time()
        else: 
            if time.time() - last_packet_time > 2.0:
                print(f"No data for 2 seconds, assuming done. Received {packet_count} packets")
                break
            # No full packet yet — give the CPU a tiny rest
            time.sleep(0.001)
        # Check how many bytes have arrived from the MCU
        while len(buffer) >= packet_size:
            # Check header
            if buffer[0] == 0xAA and buffer[1] == 0x55:
                packet = buffer[:packet_size]
                buffer = buffer[packet_size:]

                # Packet ID
                packet_id = packet[2]
                

                # Timestamp (little-endian 4 bytes)
                timestamp = struct.unpack('<I', packet[3:7])[0] # <I = interpret 4 bytes of data as a 32-bit unsigned integer in little-endian order.
                if packet_id == 1:
                    start_time = timestamp
                    print(f"Start time: {start_time}")
                sample_times = [(start_time + (packet_id - 1)*40 + i*4) / 1000.0 for i in range(10)]
                sample_times = [round(t, 4) for t in sample_times]
                print(f"Sample times: {sample_times}")
                # Samples (10 samples, 2 bytes each, little-endian)
                samples = struct.unpack('<' + 'H'*10, packet[7:27])  # H = uint16, interpret 20 bytes as 10 unsigned 16-bit integers in little-endian order.

                # End marker
                end_marker = packet[27]
                if end_marker != 0xFF:
                    print("Warning: end marker mismatch")

                with data_lock:
                    received_samples_full.extend(samples)
                    received_samples_plot.extend(samples)
                    timestamps_full.extend(sample_times)
                    timestamps_plot.extend(sample_times)

                    if len(received_samples_plot) > max_samples_plotted:
                        received_samples_plot[:] = received_samples_plot[-max_samples_plotted:]
                        timestamps_plot[:] = timestamps_plot[-max_samples_plotted:]
                # Print packet
                packet_count += 1
                print(f"Packet ID: {packet_id}, Timestamp: {timestamp}, Samples: {samples}")

            else:
                buffer = buffer[1:]
    
    print(f"Exited read loop. stop_flag={stop_flag}, packet_count={packet_count}")
    print("Full set of values: ")
    print(received_samples_full)

    

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


# ----------- PLOT FUNCTIONS --------------------
def compare_data_plots(ecg_digital):
    # plt.plot(received_samples[140:], label="Received ECG samples")
    # plt.plot(ecg_digital[270:], label = 'Database ECG Data')
    print("Showing final comparison plot...")
    plt.plot(received_samples, label="Received ECG samples")
    plt.plot(ecg_digital, label = 'Database ECG Data')

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    ax1.plot(received_samples, label="Received ECG samples")
    ax1.set_title("Received ECG Samples")
    ax2.plot(ecg_digital, label = 'Database ECG Data')
    ax2.set_title("Database ECG Data")
    plt.legend()
    plt.show()


def start_streaming_and_reading(ecg_digital):
    
    def streaming_workflow():
        """Complete streaming workflow - runs in background thread"""
        
        # Create and start read thread
        read_thread = threading.Thread(target=read_from_mcu, args=(packet_size,), daemon=True)
        read_thread.start()
        
        # Call stream() directly - it runs in THIS thread (workflow thread)
        # This blocks the workflow thread for 10 seconds, but GUI keeps running!
        stream(ecg_digital)
        
        # After streaming completes
        time.sleep(0.5)
        
        # Wait for ESP32 to finish processing
        print("Streaming complete, waiting for ESP32 to process...")
        time.sleep(5.0)
        
        # Stop reading thread
        stop_flag.set()
        read_thread.join(timeout=2)
        
        print('Finished streaming - total samples:', len(received_samples_full))
    # Start the entire workflow in a background thread
    # This returns immediately, so GUI isn't blocked
    threading.Thread(target=streaming_workflow, daemon=True).start() 
       
   

def main():

    global plot_widget, curve, status_label # global variables that will update over course of run

    # GENERATE DATASET
    ecg_digital = create_dataset(dataset_type, durations_json, bpm, fs, num_beats, open_source_time_s)
    expected_packet_num = len(ecg_digital)/10
    print(expected_packet_num)

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
    plot_widget.setLabel('left', 'ADC Value')
    plot_widget.setLabel('bottom', 'Time (s)')
    plot_widget.setTitle('Real-Time ECG Signal')
    plot_widget.showGrid(x=True, y=True)
    plot_widget.setYRange(0, 4096)  # 12-bit ADC range
    ax = plot_widget.getAxis('bottom')
    ax.setTickSpacing(major=1.0, minor=0.5)  # 1 s major, 0.5 s minor

    # Create plot line
    curve = plot_widget.plot(pen=pg.mkPen(color='#00FF00', width=2))  # Green line
    
    # Create status label
    status_label = QtWidgets.QLabel(f"Status: Ready to receive data (expecting {expected_packet_num} packets)")
    
    # Add widgets to layout
    layout.addWidget(plot_widget)
    layout.addWidget(status_label)
    
    # Setup timer to update plot periodically
    timer = QtCore.QTimer()
    timer.timeout.connect(update_plot)
    timer.start(80)  # Update every 80ms (20 FPS)

    # Start streaming in background (after small delay for GUI to load)
    QtCore.QTimer.singleShot(500, lambda: start_streaming_and_reading(ecg_digital))
    
    # Show window
    win.show()
    
    # Run Qt application
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()


