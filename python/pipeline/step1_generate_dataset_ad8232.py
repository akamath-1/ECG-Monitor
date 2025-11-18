import wfdb
import numpy as np
import matplotlib.pyplot as plt
import csv
import os
import pandas as pd

# from python.pipeline.hardware.collect_ad8232_data import main as collect_ad8232_data
# read specified dataset from ecg-monitor/datasets/AD8232/...
# create an array out of ecg_monitor

# ENTER FILE NAME HERE THAT YOU WANT TO ANALYZE (IF RUNNING AS STANDALONE FILE):
# IF RUNNING IN MASTER CONTROLLER, file_to_analyze WILL BE PASSED IN FROM collect_ad8232_data.py
file_to_analyze = "ad8232_rest_run2_30_250.csv"


def convert_analog_to_digital(analog_data_file_name):

    ADC_MAX = 4095.0
    V_MAX = 3.3
    df1 = pd.read_csv(analog_data_file_name)
    biased_voltages = df1.iloc[:, 1]  # second column
    ad8232_recorded_data_digital = [
        int(round(i / V_MAX * ADC_MAX)) for i in biased_voltages
    ]
    return ad8232_recorded_data_digital


def main(file_to_analyze="ad8232_rest_run2_30_250.csv"):
    # STEP 1: CREATE PATH FOR OUTPUT OF THIS FILE (DIGITAL DATA)

    analog_data_file_name = f"datasets/AD8232 Datasets/{file_to_analyze}"
    base_file_name = os.path.basename(
        analog_data_file_name
    )  # "ad8232_rest_run2_30_250.csv"
    base_file_name_no_ext = os.path.splitext(base_file_name)[
        0
    ]  # "ad8232_rest_run2_30_250"
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    output_dir = os.path.join(
        project_root, "data_logs", "AD8232", base_file_name_no_ext
    )
    os.makedirs(output_dir, exist_ok=True)
    final_output_path = os.path.join(output_dir, "Digital Dataset.txt")

    # STEP 2: OPEN FILE AND APPEND CONTENTS TO ARRAY
    ad8232_recorded_data_digital = convert_analog_to_digital(analog_data_file_name)

    print(f"Loaded {len(ad8232_recorded_data_digital)} samples")
    # print("ECG Data:")
    # print(ad8232_recorded_data_digital)

    # STEP 3: WRITE DIGITAL DATA TO TEXT FILE IN DESTINATION FOLDER
    with open(final_output_path, "w") as f:
        for value in ad8232_recorded_data_digital:
            f.write(f"{value}\n")

    return ad8232_recorded_data_digital


if __name__ == "__main__":
    main()
