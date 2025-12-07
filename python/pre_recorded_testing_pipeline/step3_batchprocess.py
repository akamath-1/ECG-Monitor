import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

from datetime import datetime

# ========= IMPORT CLASSES FROM CORE and STEP1 (GENERATE DATASET) ===================================================================

from python.pipeline.step1_generate_dataset_physionet import generateData
from python.pipeline.step1_generate_dataset_physionet import (
    main as generate_dataset_main,
)
from python.core.signal_processing import (
    R_peak_detector,
    BPMDetector,
    AD8232_Bandpass_Simulator,
)
from python.core.logging import CSVLogger

# ====================================================================================================================================


import csv
import os


class R_peak_detector:
    def __init__(
        self, fs=250, sec_of_calibration=2, slope_spacing=4, mov_ave_window=15
    ):
        self.fs = fs
        self.sec_of_calibration = sec_of_calibration
        self.slope_spacing = slope_spacing
        self.mov_ave_window = mov_ave_window

        self.warmup_samples = self.fs * self.sec_of_calibration
        self.refractory_samples = int(0.2 * self.fs)

        self.sample_count = 0
        self.raw_buffer = [0] * (self.slope_spacing + 5)
        self.squared_buffer = [0] * self.mov_ave_window
        self.integrated_warmup = [0] * self.warmup_samples
        self.warmup_complete = False
        self.threshold = 0.0

        self.samples_since_last_peak = self.refractory_samples + 1
        self.in_peak = False
        self.peak_start = 0
        self.peak_max_value = 0
        self.peak_max_index = 0
        self.detected_peaks = []

    def check_for_peak(self, integrated, threshold):
        self.samples_since_last_peak += 1
        if not self.in_peak:
            if (
                integrated > threshold
                and self.samples_since_last_peak > self.refractory_samples
            ):
                self.in_peak = True
                self.peak_start = self.sample_count
                self.peak_max_index = self.sample_count
                self.peak_max_value = integrated
        else:
            if integrated > self.peak_max_value:
                self.peak_max_value = integrated
                self.peak_max_index = self.sample_count
            if integrated < threshold:
                search_start = max(0, self.peak_start)
                search_end = self.sample_count
                raw_max_value = -1
                raw_max_index = self.peak_max_index
                for check_index in range(search_start, search_end):
                    buffer_pos = check_index % len(self.raw_buffer)
                    if self.raw_buffer[buffer_pos] > raw_max_value:
                        raw_max_value = self.raw_buffer[buffer_pos]
                        raw_max_index = check_index
                self.detected_peaks.append(raw_max_index)
                self.samples_since_last_peak = 0
                self.in_peak = False

    def process_sample(self, current_sample):
        len_buff = len(self.raw_buffer)
        self.raw_buffer[self.sample_count % len_buff] = current_sample

        if self.sample_count >= self.slope_spacing:
            old_sample = self.raw_buffer[
                (self.sample_count - self.slope_spacing) % len_buff
            ]
            diff = current_sample - old_sample
            squared = diff * diff
            self.squared_buffer[self.sample_count % self.mov_ave_window] = squared

            if self.sample_count >= (self.slope_spacing + self.mov_ave_window - 1):
                total = sum(self.squared_buffer)
                integrated = total / self.mov_ave_window

                if not self.warmup_complete:
                    min_samples = self.slope_spacing + self.mov_ave_window - 1
                    warmup_index = self.sample_count - min_samples
                    if warmup_index < self.warmup_samples:
                        self.integrated_warmup[self.sample_count - min_samples] = (
                            integrated
                        )
                    if self.sample_count == (self.warmup_samples + min_samples - 1):
                        self.threshold = np.percentile(self.integrated_warmup, 90)
                        self.integrated_warmup = None
                        self.warmup_complete = True
                else:
                    self.check_for_peak(integrated, self.threshold)
        self.sample_count += 1


class BPMDetector:
    def __init__(self, fs=250, window_of_averaging=5):
        self.fs = fs
        self.window_of_averaging = window_of_averaging
        self.window_samples = self.fs * self.window_of_averaging
        self.peak_history = []
        self.current_bpm = 0.0
        self.instantaneous_bpm = 0.0
        self.bpm_history = []

    def add_peak(self, sample_index, timestamp):
        self.peak_history.append((sample_index, timestamp))
        if len(self.peak_history) >= 2:
            last_peak = self.peak_history[-1]
            prev_peak = self.peak_history[-2]
            rr_interval_samples = last_peak[0] - prev_peak[0]
            rr_interval_seconds = rr_interval_samples / self.fs
            self.instantaneous_bpm = 60.0 / rr_interval_seconds
            self.bpm_history.append(round(float(self.instantaneous_bpm), 1))

    def calculate_bpm_in_window(self, current_time):
        cutoff_time = current_time - self.window_of_averaging
        peaks_in_window = [p for p in self.peak_history if p[1] >= cutoff_time]
        rr_intervals = []
        for i in range(1, len(peaks_in_window)):
            rr_samples = peaks_in_window[i][0] - peaks_in_window[i - 1][0]
            rr_seconds = rr_samples / self.fs
            rr_intervals.append(rr_seconds)
        if len(rr_intervals) > 0:
            avg_rr = np.mean(rr_intervals)
            self.current_bpm = 60.0 / avg_rr
        return self.current_bpm


class AD8232_Bandpass_Simulator:
    def __init__(self, fs=250, hp_cutoff=0.5, lp_cutoff=25, order=2):
        self.fs = fs
        self.hp_cut = hp_cutoff
        self.lp_cut = lp_cutoff
        self.order = order
        nyq = 0.5 * fs
        low = hp_cutoff / nyq
        high = lp_cutoff / nyq
        self.sos = butter(order, [low, high], btype="bandpass", output="sos")
        self.zi = sosfilt_zi(self.sos)

    def filter_array(self, data):
        y, _ = sosfilt(self.sos, data, zi=self.zi * len(data))
        return y


# ----------------------------
# BatchTester Wrapper
# ----------------------------


class BatchTester:
    """
    Runs the exact same logic as streaming mode, but on pre-recorded data.
    """

    def __init__(self, fs=250, use_filter=False):
        self.fs = fs
        self.use_filter = use_filter  # choose whether or not to apply bandpass filter
        self.detector = R_peak_detector(fs=fs)
        self.bpm_detector = BPMDetector(fs=fs)
        self.filter = AD8232_Bandpass_Simulator(fs=fs) if use_filter else None

    def run(self, data):
        if self.use_filter:
            data = self.filter.filter_array(data)

        timestamps = np.arange(len(data)) / self.fs

        for i, sample in enumerate(data):
            # Track peaks before processing
            peaks_before = len(self.detector.detected_peaks)

            self.detector.process_sample(sample)

            # Check if a new peak was just detected
            peaks_after = len(self.detector.detected_peaks)
            is_peak = peaks_after > peaks_before  # ✅ Correct check

            if is_peak:
                # Use the detected peak's index, not the current loop index
                peak_sample_index = self.detector.detected_peaks[-1]
                peak_timestamp = (
                    peak_sample_index / self.fs
                )  # Calculate timestamp from peak index

                self.bpm_detector.add_peak(peak_sample_index, peak_timestamp)
        # Calculate windowed BPM at the end using the last timestamp
        if len(timestamps) > 0:
            final_timestamp = timestamps[-1]
            final_windowed_bpm = self.bpm_detector.calculate_bpm_in_window(
                final_timestamp
            )

        return {
            "r_peaks": self.detector.detected_peaks,
            "instantaneous_bpm": self.bpm_detector.bpm_history,
            "avg_bpm_5s": self.bpm_detector.current_bpm,
        }


def main(file_name=None, output_csv_path=None, digital_dataset=None):

    if digital_dataset == None:
        file_name = file_name
        digital_dataset, r_peaks, num_peaks, inst_bpms = generate_dataset_main(
            file_name, output_csv_path=output_csv_path, bit_res=12, start_s=0, end_s=30
        )
        # print(
        #     f"Digital dataset (parsed from {file_name} to paste into Gateway MCU firmware:)"
        # )
        # print(digital_dataset)

    tester = BatchTester(fs=250, use_filter=False)
    results = tester.run(digital_dataset)

    detected_peaks = results["r_peaks"]
    bpm_history = results["instantaneous_bpm"]
    avg_bpm_5s = results["avg_bpm_5s"]

    print(f"Detected peaks: {detected_peaks}")
    print(f"BPM history (instantaneous): {bpm_history}")
    print(f"Averaged BPM (per every 5 seconds): {round(float(avg_bpm_5s),1)}")

    csv_filename = os.path.join(output_csv_path, "batch_processed_outputs.csv")

    min_len = min(len(detected_peaks) - 1, len(bpm_history))
    with open(csv_filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Detected R_peak_index", "Digital Value", "Instantaneous_BPM"])
        for i in range(min_len):
            r_index = detected_peaks[i]
            r_value_dig = digital_dataset[r_index]
            bpm = bpm_history[i]
            writer.writerow([r_index, r_value_dig, bpm])
    print(f"✅ Saved detected R-peak and BPM data (batch-processing) to {csv_filename}")
    return csv_filename


if __name__ == "__main__":
    main()
