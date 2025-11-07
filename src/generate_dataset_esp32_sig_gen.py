# Use this code to generate the data for a single heartbeat. 
# Copy-paste the generated data into firmware of the ESP32 SignalGenerator (esp32_signalgenerator.ino). 
# Note: This data must be in digital, 8-bit resolution (hence, adc_max = 255) to be streamed from the DAC of the ESP32. 

import wfdb
import numpy as np
import matplotlib.pyplot as plt

sec_ecg = 5 #CHANGE THIS TO CHANGE NUMBER OF SECONDS OF DATA TO EXTRACT FROM ECG DATA FILE
# Load ECG signal
record = wfdb.rdrecord('...data/ECG_Data_P0000/p00000_s00', sampfrom=0, sampto=250*sec_ecg) # hz * num of seconds = number of values to extract 
ecg_signal = record.p_signal[:, 0]
print(ecg_signal)
# Load annotations (beat locations)
annotation = wfdb.rdann('...data/ECG_Data_P0000/p00000_s00', 'atr', sampfrom=0, sampto=250*5)

# Get R-peak sample indices
r_peaks = annotation.sample  # Array of sample indices where beats occur
num_peaks = len(r_peaks)
print(f"Number of beats in {sec_ecg} seconds: {num_peaks}")
print(f"R-peak locations (sample indices): {r_peaks}")

#Convert single float value to digital reading (amplify by 100x, turn to voltage, add to baseline, then convert to 8-bit)
def float_to_adc(ecg_value, gain = 100, vin = 0, vref = 3.3, baseline = 1.5, adc_max = 255):
    amplified_mV = ecg_value * gain;  #e.g. 1.0 mV -> 100 mV
    amplified_V = amplified_mV / 1000; #mV -> V
    vin = baseline + amplified_V

    vin = max(0.0, min(vref, vin))  # clamp to 0..VREF
    adc = int(round((vin / vref) * adc_max))
    return adc # 0..4095

#Convert full ECG dataset to digital data
def convert_to_digital(ecg):
    ecg_digital = []
    for i in ecg:
        ecg_digital.append(float_to_adc(i))
    return ecg_digital




ecg_one_beat_length = int(len(ecg_signal)/num_peaks)
ecg_one_beat = ecg_signal[0:ecg_one_beat_length]
ecg_one_beat_digital = convert_to_digital(ecg_one_beat)

plt.plot(ecg_one_beat_digital, label = 'digital 8-bit beat')
plt.legend()
plt.show()
print("RAW DATA TO PASTE INTO FIRMWARE (ONE HEARTBEAT): ")
print(ecg_one_beat)
print(ecg_one_beat_digital)
