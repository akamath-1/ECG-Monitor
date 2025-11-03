import serial
import time
from src.heartrate_generator import generate_ecg
import matplotlib.pyplot as plt
import numpy as np


ser = serial.Serial('/dev/cu.usbserial-0001', 115200, timeout=1)
time.sleep(2)  # Wait for connection to stabilize

fs = 500
gain = 100
baseline = 1.5
adc_max = 4095
vin = 0
vref = 3.3 

durations = {
    "P": int(0.08 * fs),
    "PR": int(0.04 * fs),
    "QRS": int(0.08 * fs),
    "ST": int(0.12 * fs),
    "T": int(0.16 * fs),
    "TP": int(0.32 * fs)
}

def float_to_adc(ecg_value, gain = 100, vin = 0, vref = 3.3, baseline = 1.5, adc_max = 4095):
    amplified_mV = ecg_value * gain;  #e.g. 1.0 mV -> 100 mV
    amplified_V = amplified_mV / 1000; #mV -> V
    vin = baseline + amplified_V

    vin = max(0.0, min(vref, vin))  # clamp to 0..VREF
    adc = int(round((vin / vref) * adc_max))
    return adc # 0..4095

def convert_to_digital(ecg):
    ecg_digital = []
    for i in ecg:
        ecg_digital.append(float_to_adc(i))
    return ecg_digital

ecg_expected = generate_ecg(durations)
digital_ecg_expected = convert_to_digital(ecg_expected)

# Send a command to start streaming
ser.write(b'START\n')
digital_firmware_values = []
# Read and print 40 packets
for _ in range(42):
    line = ser.readline().decode().strip()
    if line:
        print("Received:", line)
        if line.startswith("Packet"):
            parts = line.split()
            parts = parts[2:]
            #print(parts)
            digital_firmware_values.extend([int(float(x)) for x in parts])
            #print(voltage_values)
        
digital_firmware_values = [int(x) for x in digital_firmware_values]
print(digital_firmware_values)
print(digital_ecg_expected == digital_firmware_values)
# Stop streaming
ser.write(b'STOP\n')

ser.close()

tolerance = 0.06 # is this too high? change later if needed !!
digital_firmware_values = np.array(digital_firmware_values)
ecg_expected = np.array(ecg_expected)



plt.plot(digital_ecg_expected, label="Python ECG")
plt.plot(digital_firmware_values, label="Arduino ECG")
plt.legend()
plt.show()

diff = np.abs(digital_firmware_values - digital_ecg_expected)
print(diff)
all_within_tolerance = np.all(diff < tolerance)
print(all_within_tolerance)