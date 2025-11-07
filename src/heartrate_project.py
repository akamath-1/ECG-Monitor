# This version of code now does the following:
# Parses data from a prerecorded ECG dataset (Source: Incentia 11k. Currently using data of Patient P00000, located in "data" folder.)
# Concurrently streams a generated ECG dataset to the MCU and receives packetized data for verification.
# Decodes binary packets from the firmware and compares received samples to the expected dataset.
# Produces static plots of transmitted vs received ECG signals after streaming completes.


import serial
import time
from src.heartrate_generator import create_dataset
import matplotlib.pyplot as plt
import numpy as np
import struct
import threading
import json
import wfdb


ser = serial.Serial('/dev/cu.usbserial-0001', 115200, timeout=1)
time.sleep(2)  # Wait for connection to stabilize

# Clear any leftover data in buffers
ser.reset_input_buffer()
ser.reset_output_buffer()

record = wfdb.rdrecord('../data/ECG_Data_P0000/p00000_s00', sampfrom=0, sampto=250*1)



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


def stream(ecg_digital):
    # Send a command to start streaming
    ser.write(b'START\n')
    time.sleep(0.1)
    digital_firmware_values = []
    for sample in ecg_digital:
        # Convert sample to bytes (2 bytes for 12-bit ADC)
        ser.write(int(sample).to_bytes(2, byteorder='little'))
        time.sleep(1/fs)  # maintain 500 Hz

#stop_flag = False
stop_flag = threading.Event()
#timeout = 10

def read_from_mcu(packet_size): #, expected_packet_num, timeout
    
    print("Listening for packets...\n")
    buffer = b''
    packet_count = 0
    last_packet_time = time.time()

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

                # Samples (10 samples, 2 bytes each, little-endian)
                samples = struct.unpack('<' + 'H'*10, packet[7:27])  # H = uint16, interpret 20 bytes as 10 unsigned 16-bit integers in little-endian order.

                # End marker
                end_marker = packet[27]
                if end_marker != 0xFF:
                    print("Warning: end marker mismatch")

                received_samples.extend(samples)
                # Print packet
                packet_count += 1
                print(f"Packet ID: {packet_id}, Timestamp: {timestamp}, Samples: {samples}")

            else:
                buffer = buffer[1:]
    print(f"Exited read loop. stop_flag={stop_flag}, packet_count={packet_count}")
    # print("Samples received: ")
    # print(received_samples)
    # print("Length of samples: ")
    # print(len(received_samples))


# GENERATE DATASET
ecg_digital = create_dataset(dataset_type, durations_json, bpm, fs, num_beats, open_source_time_s)
expected_packet_num = len(ecg_digital)/10
print(expected_packet_num)


# CREATE THREADS
stream_thread = threading.Thread(target=stream, args=(ecg_digital,))
read_thread = threading.Thread(target=read_from_mcu, args=(packet_size,))

# STREAM DATA TO MCU, STREAM PACKETS FROM MCU
read_thread.start()
stream_thread.start()
stream_thread.join()


time.sleep(0.5)

# Wait for ESP32 to finish processing
print("Streaming complete, waiting for ESP32 to process...")
time.sleep(5.0)

# Now stop reading
stop_flag.set()
read_thread.join()

print('finished streaming')


plt.plot(received_samples, label="Received ECG samples")
plt.plot(ecg_digital, label = 'Database ECG Data')

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
ax1.plot(received_samples, label="Received ECG samples")
ax1.set_title("Received ECG Samples")
ax2.plot(ecg_digital, label = 'Database ECG Data')
ax2.set_title("Database ECG Data")
plt.legend()
plt.show()
