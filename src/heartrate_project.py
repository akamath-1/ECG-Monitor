# This version of code now implements modular, class-based architecture for streamed data visualization
# and CSV logging.
# Classes written: Packet, PacketParser, CSVLogger classes + Synthetic_Data_Config and Incentia_Data_Config.
# Code now handles threaded CSV writing and generates run metadata post-streaming (streaming shut-down
# handled now via GUI close).
# 


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
import queue
import csv
import datetime
import os

hr_config_path = os.path.join(os.path.dirname(__file__), "heartrate_config.json")
ecg_data_path = os.path.join(os.path.dirname(__file__), "..", "data", "ECG_Data_P0000", "p00000_s00")

class Packet:
    # Represents a single parsed packet with its attributes
    
    def __init__(self, packet_id, timestamp, samples, sample_times):
        self.packet_id = packet_id
        self.timestamp = timestamp
        self.samples = samples
        self.sample_times = sample_times
    
    def __repr__(self):
        return f"Packet(ID={self.packet_id}, timestamp={self.timestamp}, samples={len(self.samples)})"
    
class PacketParser():
    def __init__(self, packet_size):
        self.packet_size = packet_size
        self.buffer = b''
        self.HEADER_1 = 0xAA
        self.HEADER_2 = 0x55
        self.END_MARKER = 0xFF
        self.NUM_SAMPLES = 10
        self.SAMPLE_INTERVAL_MS = 4
        self.packet_count = 0

    def update_buffer(self, data):
        self.buffer += data

    def has_complete_packet(self):
        return len(self.buffer) >= self.packet_size

    def get_packet(self):
        # Not enough bytes yet
        if len(self.buffer) < self.packet_size:
            return None # What does this do
        
        # Check header
        if self.buffer[0] != self.HEADER_1 or self.buffer[1] != self.HEADER_2:
            self.buffer = self.buffer[1:]  # Shift by 1 and retry
            return None
        
        # Extract packet
        packet = self.buffer[:self.packet_size]
        self.buffer = self.buffer[self.packet_size:]
        
        # Check footer
        if packet[-1] != self.END_MARKER:
            print("End marker mismatch, resyncing...")
            # Resync: find next header
            while len(self.buffer) >= 2 and not (self.buffer[0] == self.HEADER_1 and self.buffer[1] == self.HEADER_2):
                self.buffer = self.buffer[1:]
            return None
        
        # Parse all fields at once
        packet_id = packet[2]
        timestamp = struct.unpack('<I', packet[3:7])[0]
        samples = struct.unpack('<' + 'B'*10, packet[7:17])

        # Calculate sample times
        sample_times = [(timestamp + i*4) / 1000.0 for i in range(10)]
        sample_times = [round(t, 4) for t in sample_times]
        
        # Return Packet object
        return Packet(packet_id, timestamp, samples, sample_times)

class Synthetic_Data_Config():
    def __init__(self, config_file=hr_config_path):
        with open(config_file) as f:
            config = json.load(f)

        self.bpm = config["bpm"]
        self.fs = config["sampling_hz"]
        self.num_beats = 2 #config["num_beats"]
        self.heartbeat_type = config["heartbeat_type"]
        self.durations_json = config["durations"]
        self.packet_size = 18
        self.dataset_type = config["type_of_data"] 
        self.received_samples = []
        self.plot_window_s = config["plot_window_s"]
        self.max_samples_plotted = int(self.fs * self.plot_window_s)

    def __repr__(self):
        return f"Config(bpm={self.bpm}, sampling_hz={self.fs}, packet_size={self.packet_size})"

class Incentia_Data_Config():
    def __init__(self, config_file=hr_config_path):
        with open(config_file) as f:
            config = json.load(f)
        self.fs = config["sampling_hz"]
        self.open_source_time_s = config["open_source_time_s"]
        self.packet_size = 18
        self.received_samples = []
        self.plot_window_s = config["plot_window_s"]
        self.max_samples_plotted = int(self.fs * self.plot_window_s)

    def __repr__(self):
        return f"Config(sampling_hz={self.fs}, packet_size={self.packet_size})"


class CSVLogger():
    def __init__(self, file_name, stop_flag, write_interval=1.0):
        self.file_name = file_name
        self.csv_queue = queue.Queue()
        self.stop_flag = stop_flag 
        self.samples_written = 0
        self._thread = None
        self.write_interval = write_interval
        self.start_time = None
        self.stop_time = None
        self.metadata_file = "run_metadata.json"

    def create_CSV(self):
        #self.start_time = datetime.datetime.now().isoformat()
        with open(self.file_name, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Time', 'Sample', 'Packet ID', 'Packet Count'])
        
        self._thread = threading.Thread(target=self.write_batch_to_csv, daemon=False)
        self._thread.start()

    def log(self, timestamp, value, packet_id, packet_count):
        """Add a sample to the queue (thread-safe)"""
        self.csv_queue.put([timestamp, value, packet_id, packet_count])


    def write_batch_to_csv(self):
        batch = []
        while not stop_flag.is_set():
            time.sleep(self.write_interval)  # Wait 1 second between writes
            
            while not self.csv_queue.empty():
                try:
                    entry = self.csv_queue.get(block=False)
                    batch.append(entry)
                except queue.Empty:
                    break
            if len(batch) > 0:
                with open(self.file_name, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(batch)  # Write all rows at once
                
                self.samples_written += len(batch)
                print(f"Wrote {len(batch)} samples to CSV (total: {self.samples_written})")
                batch.clear()
            
        print("Streaming stopped, writing remaining data...")
        final_batch = []
        while not self.csv_queue.empty():
            try:
                item = self.csv_queue.get(block=False)
                final_batch.append(item)
            except queue.Empty:
                break
        
        if len(final_batch) > 0:
            with open(self.file_name, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(final_batch)
            self.samples_written += len(final_batch)
            print(f"📝 Final write: {len(final_batch)} samples")

        self.stop_time = datetime.datetime.now().isoformat()
        print(f"✅ CSV writer finished. Total samples written: {self.samples_written}")
        self.save_metadata()

    def save_metadata(self):
        """Write metadata about run timing and totals to JSON"""
        metadata = {
            "csv_file": self.file_name,
            "start_time": self.start_time,
            "stop_time": self.stop_time,
            "samples_written": self.samples_written
        }
        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=4)
        print(f"Saved metadata to {self.metadata_file}")

# GLOBAL VARIABLES ====================================================================================

ser = serial.Serial('/dev/cu.usbserial-0001', 115200, timeout=1)
time.sleep(2)  # Wait for connection to stabilize

# Clear any leftover data in buffers
ser.reset_input_buffer()
ser.reset_output_buffer()

record = wfdb.rdrecord(ecg_data_path, sampfrom=0, sampto=250*1)


# Shared data between threads
received_samples_full = [] # NEW
received_samples_plot = [] # NEW
timestamps_full = [] # NEW
timestamps_plot = [] # NEW

data_lock = threading.Lock()  # NEW - Protect received_samples
stop_flag = threading.Event()
stop_flag.is_set()
# NEW - PyQtGraph globals (will be initialized in main)
plot_widget = None
curve = None
status_label = None

#========================================================================================================================

# THREAD 1
def read_from_mcu(config, csv_logger): #, expected_packet_num, timeout
    
    parser = PacketParser(config.packet_size)
    print("Listening for packets...\n")
    
    packet_count = 0
    last_packet_time = time.time()
    start_time = 0
    while not stop_flag.is_set(): #while stop != true, aka while "going"
        #add bytes from the serial port to the buffer array
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting) #if bytes in the serial port, read them
            parser.update_buffer(data) #add bytes to buffer
            last_packet_time = time.time()
        else: 
            if time.time() - last_packet_time > 2.0:
                print(f"No data for 2 seconds, assuming done. Received {packet_count} packets")
                break
            # No full packet yet — give the CPU a tiny rest
            time.sleep(0.001)
        # Check how many bytes have arrived from the MCU
        if b'RESET_REASON' in parser.buffer:
            print(f"⚠️ ESP32 RESET DETECTED: {data}")
        if b'BOOT_TIME' in parser.buffer:
            print(f"⚠️ ESP32 RESTARTED: {data}")

        while len(parser.buffer) >= config.packet_size: #when bytes in buffer > packet size (18 for 8-bit)
            packet = parser.get_packet()
            # Check header
            if packet is None:
                continue
            parser.packet_count += 1
            print(f"Packet ID: {packet.packet_id}, Packet Count: {parser.packet_count}, Timestamp: {packet.timestamp}, Samples: {packet.samples}")
            
            if parser.packet_count == 1:
                csv_logger.start_time = datetime.datetime.now().isoformat()
            for i in range(len(packet.samples)):
                csv_logger.log(packet.sample_times[i], packet.samples[i], packet.packet_id, parser.packet_count) 
           
            with data_lock:
                received_samples_full.extend(packet.samples)
                received_samples_plot.extend(packet.samples)
                timestamps_full.extend(packet.sample_times)
                timestamps_plot.extend(packet.sample_times)

                if len(received_samples_plot) > config.max_samples_plotted:
                    received_samples_plot[:] = received_samples_plot[-config.max_samples_plotted:]
                    timestamps_plot[:] = timestamps_plot[-config.max_samples_plotted:]
            
    
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





def start_streaming_from_mcu(config, csv_logger):
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
    mcu_read_thread = threading.Thread(target=read_from_mcu, args=(config, csv_logger), daemon=True)
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
    
    eeg_config = Incentia_Data_Config(hr_config_path)
    csv_logger = CSVLogger("heartrate_csv.csv", stop_flag)
    

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
    
    def on_window_close(event):
        print("Window is closing! Stopping threads...")
        stop_flag.set()      # Tell all threads to stop
        ser.write(b'STOP\n') # Tell the MCU to stop
        
        # Wait for the logger thread to finish its final write
        if csv_logger._thread:
             csv_logger._thread.join(timeout=2.0)
        
        event.accept() # Allow the window to close
    win.closeEvent = on_window_close
    # Setup timer to update plot periodically
    timer = QtCore.QTimer()
    timer.timeout.connect(update_plot)
    timer.start(200)  # Update every 80ms (20 FPS)

    def start_everything():
        csv_logger.create_CSV()  # Start CSV logger thread
        start_streaming_from_mcu(eeg_config, csv_logger)
        thread_stop_command()
    
    # Start streaming in background (after small delay for GUI to load)
    QtCore.QTimer.singleShot(500, start_everything)
    # Show window
    win.show()
    
    # Run Qt application
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()




