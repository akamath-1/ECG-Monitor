import numpy as np
import matplotlib.pyplot as plt


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


fs = 500          # Sampling frequency (Hz)
bpm = 75
beat_period = 60 / bpm   # 0.8 s
samples = int(fs * beat_period)

# --- Define durations (in samples) ---
durations = {
    "P": int(0.08 * fs),
    "PR": int(0.04 * fs),
    "QRS": int(0.08 * fs),
    "ST": int(0.12 * fs),
    "T": int(0.16 * fs),
    "TP": int(0.32 * fs)
}

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

# Analog to Digital Conversion of voltage

def voltage_ADC(ecg):
    ecg_amplified_mV = ecg * 100 #amplify mV by 100x
    ecg_adjusted = ecg_amplified_mV/1000 + 1.5 #convert to V from mV, then add 1.5V to bring to baseline
    return ecg_adjusted

# --- Combine all segments ---
def generate_ecg(durations):
    ecg = np.concatenate([
        p_wave(durations["P"]),
        flat(durations["PR"]),
        qrs_complex(durations["QRS"]),
        flat(durations["ST"]),
        t_wave(durations["T"]),
        flat(durations["TP"])
    ])
    return ecg

# ecg_new = voltage_ADC(ecg)
# print(ecg_new)

ecg = generate_ecg(durations)
# # --- Plot ---
# time = np.linspace(0, beat_period, len(ecg))
# plt.plot(time, ecg)
# plt.title("Synthetic ECG - 75 BPM, 500 Hz Sampling")
# plt.xlabel("Time (s)")
# plt.ylabel("Amplitude (mV)")
# plt.grid(True)
# plt.show()


