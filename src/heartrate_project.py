# This version of the code now does the following:
# Receives, deconstructs, and graphs packets of data from MCU in real time.
# Note 1: This data is being generated from a second ESP32 (code in esp32_signalgenerator.ino), 
# and is streamed in 8-bit resolution (as opposed to 12-bit resolution, as the data being generated was before).
# The code has been changed to support conversion of data streamed at 8-bit resolution accordingly - these changes 
# will need to be reverted if/when using 12-bit resolution data in future development.
# Note 2: The code now utilizes live time-stamps read from data packets to create data arrays for graphing. 

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
packet_size = 18
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
stop_flag.is_set()
# NEW - PyQtGraph globals (will be initialized in main)
plot_widget = None
curve = None
status_label = None


# THREAD 1
def read_from_mcu(packet_size): #, expected_packet_num, timeout
    
    print("Listening for packets...\n")
    buffer = b''
    packet_count = 0
    last_packet_time = time.time()
    start_time = 0
    while not stop_flag.is_set(): #while stop != true, aka while "going"
        #add bytes from the serial port to the buffer array
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting) #if bytes in the serial port, read them
            buffer += data #add bytes to buffer
            last_packet_time = time.time()
        else: 
            if time.time() - last_packet_time > 2.0:
                print(f"No data for 2 seconds, assuming done. Received {packet_count} packets")
                break
            # No full packet yet — give the CPU a tiny rest
            time.sleep(0.001)
        # Check how many bytes have arrived from the MCU

        while len(buffer) >= packet_size: #when bytes in buffer > packet size (18 for 8-bit)
            # Check header
            if buffer[0] != 0xAA or buffer[1] != 0x55:
                buffer = buffer[1:]
                continue
            
            
            packet = buffer[:packet_size]
            #print(packet)
            buffer = buffer[packet_size:]
            #print(buffer)

            if packet[-1] != 0xFF:
                print(" End marker mismatch, resyncing...")
                while len(buffer) >= 2 and not (buffer[0] == 0xAA and buffer[1] == 0x55):
                     buffer = buffer[1:]
                continue
            # Packet ID
            packet_id = packet[2]
            

            # Timestamp (little-endian 4 bytes)
            timestamp = struct.unpack('<I', packet[3:7])[0] # <I = interpret 4 bytes of data as a 32-bit unsigned integer in little-endian order.
            # if packet_id == 1:
            #     start_time = timestamp
            #     print(f"Start time: {start_time}")
            sample_times = [(timestamp + i*4) / 1000.0 for i in range(10)]
            sample_times = [round(t, 4) for t in sample_times]
            print(f"Sample times: {sample_times}")
            # Samples (10 samples, 2 bytes each, little-endian)
            samples = struct.unpack('<' + 'B'*10, packet[7:17])  # H = uint16, interpret 20 bytes as 10 unsigned 16-bit integers in little-endian order.

           
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

            
    
    print(f"Exited read loop. stop_flag={stop_flag}, packet_count={packet_count}")
    print("Full set of values: ")
    print(received_samples_full)
    
def keyboard_listener():
    while True:
        cmd = input("Type STOP to halt data stream: ").strip().upper()
        if cmd == "STOP":
            ser.write(b'STOP\n')
            stop_flag.set()
            print("Stop flag set.")
            break

def thread_stop_command():
    listen_for_stop_thread = threading.Thread(target=keyboard_listener, daemon = True)
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





def start_streaming_from_mcu():
    stop_streaming_from_mcu()
    with data_lock:
        received_samples_full.clear() #clear array of all received samples
        received_samples_plot.clear() #clear array of plotted samples
        timestamps_full.clear() #clear array of all timestamps
        timestamps_plot.clear() #clear array of plotted timestamps
    # stop_flag.clear() #reset stop flag to false, so thread is running
    # ser.reset_input_buffer() #clear bytes in cue to be read from MCU 
    # ser.reset_output_buffer() #clear bytes in cue to be sent to MCU


    ser.write(b'START\n')     # <--- tell firmware to start
    time.sleep(0.1)
    mcu_read_thread = threading.Thread(target=read_from_mcu, args=(packet_size,), daemon=True)
    mcu_read_thread.start()
    
def stop_streaming_from_mcu():
    stop_flag.set()
    ser.write(b'STOP\n')
    time.sleep(0.05)      # let firmware stop
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    stop_flag.clear()

  
def main():

    global plot_widget, curve, status_label # global variables that will update over course of run
    with data_lock:
        received_samples_full.clear()
        received_samples_plot.clear()
        timestamps_full.clear()
        timestamps_plot.clear()
    stop_flag.clear()
    ser.reset_input_buffer()
    ser.reset_output_buffer()

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
    plot_widget.setYRange(90, 120)  # 8-bit ADC range
    ax = plot_widget.getAxis('bottom')
    ax.setTickSpacing(major=1.0, minor=0.5)  # 1 s major, 0.5 s minor

    # Create plot line
    curve = plot_widget.plot(pen=pg.mkPen(color='#00FF00', width=2))  # Green line
    
    # Create status label
    status_label = QtWidgets.QLabel(f"Status: Ready to receive data ") #(expecting {expected_packet_num} packets)")
    
    # Add widgets to layout
    layout.addWidget(plot_widget)
    layout.addWidget(status_label)
    
    # Setup timer to update plot periodically
    timer = QtCore.QTimer()
    timer.timeout.connect(update_plot)
    timer.start(200)  # Update every 80ms (20 FPS)

    # Start streaming in background (after small delay for GUI to load)
    QtCore.QTimer.singleShot(500, lambda: (start_streaming_from_mcu(), thread_stop_command()))
    
    # Show window
    win.show()
    
    # Run Qt application
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()




