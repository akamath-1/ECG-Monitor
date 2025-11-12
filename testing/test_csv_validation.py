import pytest
import pandas as pd
import numpy as np
import json
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime
import os

# VERSION 1: THIS TEST SUITE IS FOR 8-BIT RESOLUTION, PRE-RECORDED INTENTIA DATA. 
# CHANGE PARAMETERS FOR SAMPLE RANGE IF SHIFTING TO 12-BIT.

'''
This is the first set of tests developed to test data that is being streamed from the gateway MCU to the host device.
Test have been created for:
- testing time interval of data points for consistency with expected sampling rate
- testing headings of CSV and structure of recorded contents
- testing number and completeness of packets (test for dropped, partial packets)
- testing duration of CSV and length of actual data run
- a sample CSV (heartrate_csv_1.csv) has been included in the testing folder
'''
@pytest.fixture
def config():
    """Load configuration from JSON file"""
    config_path = Path(__file__).parent / "heartrate_config.json"
    
    if not config_path.exists():
        pytest.skip("Config file not found")
    
    with open(config_path) as f:
        return json.load(f)

@pytest.fixture
def sampling_rate(config):
    """Get expected sampling rate from config"""
    return config["sampling_hz"]

@pytest.fixture
def run_metadata():
    config_path = Path(__file__).parent / "run_metadata.json"
    with open(config_path) as f:
        return json.load(f)


@pytest.fixture
def csv_data():
    csv_path = Path(__file__).parent / "heartrate_csv_1.csv" #Path("heartrate_csv_1.csv")
    
    # Check if CSV exists
    if not csv_path.exists():
        print("Current working directory:", os.getcwd())
        pytest.skip("CSV file not found. Run the ECG monitor first to generate data.")
    
    heartrate_df = pd.read_csv(csv_path)
    
    # Validate basic structure
    required_columns = ['Time', 'Sample', 'Packet ID', 'Packet Count']
    missing_cols = [col for col in required_columns if col not in heartrate_df.columns]
    
    if missing_cols:
        pytest.fail(f"CSV missing required columns: {missing_cols}")
    
    # Check if CSV has data
    if len(heartrate_df) == 0:
        pytest.fail("CSV file is empty")
    
    
    return heartrate_df

#this test checks for time repeats AND large deviations in time (gaps in time, rewinded time)
def test_time_interval_ms(csv_data, sampling_rate):
    #first column is time
    
    time_arr = np.array(csv_data['Time'], dtype=np.float64)
    interval = float(1.0/sampling_rate)
    diffs = np.diff(time_arr)
    values_failed = []

    for i in range(len(diffs)):
        if not np.isclose(diffs[i], interval, atol=1e-3): #tolerance of +- 0.001 (0.003 - 0.005 seconds)
            print([i, time_arr[i], diffs[i]])
            values_failed.append(float(time_arr[i]))
    print(values_failed)
    print(f"Mean Δt: {diffs.mean():.4f}, Expected: {interval:.4f}")
    assert np.allclose(diffs, interval, atol=1e-3), \
        f"Timestamps not evenly spaced — failed values at time(s): {values_failed}."
    
#look for complete packet transmission, correct Packet Count, correct Packet ID
def test_packets(csv_data):

    time_np = np.array(csv_data['Time'], dtype=np.float64)
    duration = time_np[-1] - time_np[0]
    packet_id_np = np.array(csv_data['Packet ID'])
    packet_count_np = np.array(csv_data['Packet Count'])
    
    #Full packet transmission
    assert len(time_np)%10 == 0, \
    f"Incomplete packet transmission."

    #Full Packet Count (no mixed up or repeat packets)
    num_packets = int(len(time_np)/10)
    row_index = 0
    while row_index < len(packet_count_np):
        for i in range(num_packets):
            count_check = np.array(packet_count_np[row_index: row_index + 10])
            id_check = np.array(packet_id_np[row_index: row_index + 10])

            #check Packet Count
            assert np.all(count_check == i+1), \
            f'Packet count anomaly detected for Packet {i+1}'

            #check Packet ID
            assert np.all(id_check == (i) % 255 + 1), \
            f'Packet ID anomaly detected for Packet {i+1}'
            row_index += 10

def test_signal_range(csv_data):
    data_np = np.array(csv_data['Sample'])
    assert np.all((data_np < 255) & (data_np > 0)), \
    f'Data out of range.'


def test_csv_duration(csv_data, run_metadata):
    #calculate expected duration
    start_record = datetime.fromisoformat(run_metadata["start_time"])
    stop_record = datetime.fromisoformat(run_metadata["stop_time"])
    expect_record_duration = (stop_record - start_record).total_seconds()
    print(f"Expected time: {expect_record_duration}")
    #calculate CSV duration
    time_np = np.array(csv_data['Time'], dtype=np.float64)
    csv_duration = time_np[-1] - time_np[0]
    print(f"Actual time: {csv_duration}")
    #tolerance for error = 5%
    tol = expect_record_duration * 0.1  
    # expected vs actual durations may differ by up to ~10% due to firmware-host latency, USB buffering, and thread teardown time.

    assert run_metadata['samples_written'] == len(time_np)
    assert abs(csv_duration - expect_record_duration) < tol, \
    f"CSV duration {csv_duration:.2f}s doesn't match run time {expect_record_duration:.2f}s"
    