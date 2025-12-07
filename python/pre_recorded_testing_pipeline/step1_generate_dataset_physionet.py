import wfdb
import numpy as np
import matplotlib.pyplot as plt
import csv
import os


class generateData:
    def __init__(
        self,
        file_name="ECG_Data_P0000/p00000_s00",
        bit_res=12,
        start_s=0,
        end_s=30,
        sec_calibration=2,
    ):
        self.file_name = file_name
        self.bit_res = bit_res
        self.adc_max = 2**bit_res - 1
        self.start_s = start_s
        self.end_s = end_s
        self.gain = 500
        self.baseline = 1.5
        self.vin = 0
        self.vref = 3.3
        self.sampling_rate = 250
        self.sec_calibration = sec_calibration

    def parse_data(self):

        record = wfdb.rdrecord(
            self.file_name,
            sampfrom=self.start_s,
            sampto=self.sampling_rate * self.end_s,
        )  # hz * num of seconds = number of values to extract
        ecg_signal = record.p_signal[:, 0]
        # print(ecg_signal)
        # Load annotations (beat locations)
        annotation_total = wfdb.rdann(
            self.file_name,
            "atr",
            sampfrom=self.start_s,
            sampto=self.sampling_rate * self.end_s,
        )
        annotation = wfdb.rdann(
            self.file_name,
            "atr",
            sampfrom=self.sec_calibration,
            sampto=self.sampling_rate * self.end_s,
        )

        all_r_peaks = (
            annotation_total.sample
        )  # Array of sample indices where beats occur
        # Filter out peaks that occur during calibration period
        calibration_samples = int(
            self.sec_calibration * self.sampling_rate
        )  # e.g., 2 * 250 = 500

        # Get R-peak sample indices post-calibration
        r_peaks = all_r_peaks[
            all_r_peaks >= calibration_samples
        ]  # Only peaks after calibration
        num_peaks = len(r_peaks)

        # Get instantaneous BPMs:
        inst_bpms = [
            round(float(60 / ((r_peaks[i + 1] - r_peaks[i]) / self.sampling_rate)), 1)
            for i in range(len(r_peaks) - 1)
        ]

        print(
            f"Number of beats from {self.start_s} to {self.end_s} seconds: {num_peaks}"
        )
        print(f"R-peak locations (sample indices): {r_peaks}")
        print(f"Annotated BPM values (instantaneous): {inst_bpms}")

        return ecg_signal, r_peaks, num_peaks, inst_bpms

    def float_to_adc(self, ecg_value):
        amplified_mV = ecg_value * self.gain
        # e.g. 1.0 mV -> 100 mV
        amplified_V = amplified_mV / 1000
        # mV -> V
        vin = self.baseline + amplified_V

        vin = max(0.0, min(self.vref, vin))  # clamp to 0..VREF
        adc = int(round((vin / self.vref) * self.adc_max))
        return adc

    # Convert full ECG dataset to digital data
    def convert_to_digital(self, ecg_raw_data):
        """Convert an entire ECG dataset from mV to ADC codes."""
        return [self.float_to_adc(i) for i in ecg_raw_data]


def main(
    file_name="ECG_Data_P0000/p00000_s00",
    # patient_id="P00000",
    # segment_id="s00",
    output_csv_path=None,
    bit_res=12,
    start_s=0,
    end_s=30,
):

    dataset_generator = generateData(
        file_name, bit_res=bit_res, start_s=start_s, end_s=end_s
    )  # creates array of raw data from Incentia dataset (analog, mV)
    raw_dataset, r_peaks, num_peaks, inst_bpms = dataset_generator.parse_data()
    digital_dataset = dataset_generator.convert_to_digital(raw_dataset)
    # print(f"Digital dataset (parsed from {file_name} to paste into Gateway MCU firmware:)")
    # print(digital_dataset)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    data_logs_dir = os.path.join(project_root, "data_logs")

    # Folder will be named like: "P00000_s00"
    # output_folder_name = f"{patient_id}_{segment_id}"
    # output_dir = os.path.join(data_logs_dir, output_folder_name)

    # Create folder if it doesn’t exist
    # os.makedirs(output_dir, exist_ok=True)

    # Define the annotated output CSV path
    annotated_csv_path = os.path.join(output_csv_path, "annotated_outputs.csv")

    # output_dir = f"_rpeaks_bpm/{os.path.basename(file_name)}"
    # os.makedirs(output_dir, exist_ok=True)
    # csv_filename = os.path.join(output_dir, "annotated_outputs.csv")

    # output_dir = "ecg_outputs_rpeaks_bpm"
    # os.makedirs(output_dir, exist_ok=True)
    # csv_filename = os.path.join(output_dir, f"{os.path.basename(dataset_generator.file_name)}_annotated_outputs.csv")

    min_len = min(len(r_peaks) - 1, len(inst_bpms))
    with open(annotated_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["R_peak_index", "Analog Value", "Digital Value", "Instantaneous_BPM"]
        )
        for i in range(min_len):
            r_index = r_peaks[i]
            r_value_an = float(
                raw_dataset[r_index]
            )  # actual ECG amplitude at that R-peak
            r_value_dig = digital_dataset[r_index]
            bpm = inst_bpms[i]
            writer.writerow([r_index, round(r_value_an, 3), r_value_dig, bpm])

    print(f"✅ Saved R-peak and BPM data to {annotated_csv_path}")

    raw_data_path = os.path.join(output_csv_path, "ECG Digital Dataset.csv")

    with open(raw_data_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Expected (Calculated in SW)"])
        for i in range(len(digital_dataset)):
            writer.writerow([digital_dataset[i]])
    return digital_dataset, r_peaks, num_peaks, inst_bpms


if __name__ == "__main__":
    main()
