# updated to include provision to parse from prerecorded dataset (variables added into heartrate_config.json as well)

import numpy as np
import matplotlib.pyplot as plt
import json
import wfdb
import os

# parts of heart beat:
# P = small Gaussian/sin bump
# QRS = sharp triangle/narrow spike
# T = broader Gaussian, sin bump
# baseline = flat line
# ECG Component	Duration (s)	Voltage (mV)	Description
# P wave	    0.1	             +0.25	        Atrial depolarization
# PR segment	0.1	               0.0	        AV node delay
# QRS complex	0.08	        +1.0 (peak)	    Ventricular depolarization
# ST segment	0.1	              0.0	        Plateau (ventricular contraction)
# T wave	    0.16	            +0.3	    Ventricular repolarization
# TP segment	0.26	         0.0	        Heart at rest
hr_config_path = os.path.join(os.path.dirname(__file__), "heartrate_config.json")
ecg_data_path = os.path.join(os.path.dirname(__file__), "..", "data", "ECG_Data_P0000", "p00000_s00")

with open(hr_config_path) as f:
    config = json.load(f)

dataset_type = config["type_of_data"] 
bpm = config["bpm"]
fs = config["sampling_hz"]
num_beats = config["num_beats"]
heartbeat_type = config["heartbeat_type"]
durations_json = config["durations"]
open_source_time_s = config["open_source_time_s"]
print(open_source_time_s)

gain = 100
baseline = 1.5
adc_max = 4095
vin = 0
vref = 3.3 




# --- Define durations (in samples) ---
# durations = {
#     "P": int(0.1 * samples),
#     "PR": int(0.05 * samples),
#     "QRS": int(0.1 * samples),
#     "ST": int(0.15 * samples),
#     "T": int(0.2 * samples),
#     "TP": int(0.4 * samples)
# }



# --- Generate waveform parts ---
def p_wave(n):
    t = np.linspace(0, np.pi, n)
    return 0.25 * np.sin(t)  # mV

def qrs_complex(n):
    q = int(n * 0.25)
    r = int(n * 0.5)
    s = n - q - r
    return np.concatenate([
        -0.1 * np.linspace(0, 1, q),
        np.linspace(-0.1, 1.0, r),
        np.linspace(1.0, 0, s)
    ])

def t_wave(n):
    t = np.linspace(0, np.pi, n)
    return 0.35 * np.sin(t)

# Flat segments
def flat(n):
    return np.zeros(n)

#Convert single float value to digital reading (amplify by 100x, turn to voltage, add to baseline, then convert to 12bit)
def float_to_adc(ecg_value, gain = 100, vin = 0, vref = 3.3, baseline = 1.5, adc_max = 4095):
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
# --- Combine all segments ---
def generate_ecg(durations_json, bpm, fs, num_beats):
    beat_period = 60 / bpm   # seconds per heart beat
    total_samples = int(fs * beat_period) # total samples based on bpm and sampling rate
    durations = {key: int(value * total_samples) for key, value in durations_json.items()}

    ecg = np.concatenate([
        p_wave(durations["P"]),
        flat(durations["PR"]),
        qrs_complex(durations["QRS"]),
        flat(durations["ST"]),
        t_wave(durations["T"]),
        flat(durations["TP"])
    ])

    ecg = np.tile(ecg, num_beats)
    return ecg


# ecg_new = voltage_ADC(ecg)
# print(ecg_new)

def create_dataset(dataset_type, durations_json, bpm, fs, num_beats, open_source_time_s):
    if dataset_type == "open-source":
        ecg = wfdb.rdrecord(ecg_data_path, sampfrom=0, sampto=250*open_source_time_s)
        ecg = ecg.p_signal.flatten()
    else:
        ecg = generate_ecg(durations_json, bpm, fs, num_beats)
    ecg_digital = convert_to_digital(ecg)
    ecg_digital = np.array(ecg_digital)
    return ecg_digital

ecg_digital = create_dataset(dataset_type, durations_json, bpm, fs, num_beats, open_source_time_s)


