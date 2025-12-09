# Usage Guide

How to run the ECG Monitor testing pipelines.

> **Note**: This guide currently covers how to use the two testing frameworks in this repository: 1) the prototype testing framework and 2) the pre-recorded data testing framework. 

---

## Table of Contents

- [Overview](#overview)
- [Prototype Testing Framework](#prototype-testing-framework)
- [Pre-Recorded Data Testing Framework](#pre-recorded-data-testing-framework)
    - [PhysioNet Validation Pipeline](#physionet-validation-pipeline)
    - [AD8232 Hardware Validation Pipeline](#ad8232-hardware-validation-pipeline)
    - [Individual Pipeline Steps (Pre-Recorded Testing)](#individual-pipeline-steps-pre-recorded-testing)
- [Collecting AD8232 Data for Pre-Recorded Testing](#collecting-ad8232-data-for-pre-recorded-testing)
- [Configuration](#configuration)

---

## Overview
There are two frameworks that have been built so far:
1) Prototype testing framework (accommodates testing end-to-end pipeline, from ECG data acquisition to post-processing ECG data analysis)
2) Beat-detection algorithm validation framework (accommodates testing with pre-recorded ECG datasets)

The prototype testing framework has one pipeline, which integrates real-time ECG signal acquisition with the AD8232, wireless data transmission to the host device, and real-time and post-collection analysis of the heartrate data. 

The beat-detection validation framework provides two main pipelines:
1. **PhysioNet Pipeline** - Validates algorithm against clinical datasets with ground-truth annotations
2. **AD8232 Pipeline** - Validates algorithm with hardware-collected ECG data

Both the PhysioNet and AD8232 pipelines automate the validation workflow for the beat-detection algorithm, from data processing to comparison visualization.


---
## **Prototype Testing Framework**

## Quick Start

Run the complete real-time AD8232 acquisition pipeline:

```bash
python3 -m python.real_time_testing_pipeline.stream_and_analyze_ecg_realtime
```

## User Prompts
The pipeline will interactively prompt you for: 

File Name:   
Enter a descriptive name for the dataset using only letters, numbers, and underscores (_). File name cannot start with underscore.  
Example: walking_run1 or rest_baseline  
Validates format before proceeding

Recording Duration:  
Enter time in seconds (integer between 10-120).  
Recording automatically stops after this duration

File Overwrite Check:  
Checks if a file with this name already exists  
Option [O]: Overwrite the existing file  
Option [R]: Rename and choose a different file name  

Firmware Flash:  
Choose whether to flash new firmware to ESP32  
Enter Y to flash firmware (required for first run or firmware changes)  
Enter N to skip (if firmware already uploaded)  

Metadata Notes:  
After data collection, add optional notes  
Describe testing conditions (e.g., "subject at rest, seated")  
Press Enter twice when finished  
Type 'skip' to skip notes  

**Example**:  
Please enter the file name you would like to assign to this dataset.  
Use only letters and numbers in the name, and connect all words with "_". (ex: walking_run1): jogging_run3  
File name 'jogging_run3' is valid.  

Enter the time in seconds for recording duration (between 10 and 120): 30  
Duration set to 30 seconds.  

Flash firmware to ESP32? Please enter Y/N: n

## What it Does
1) Flash Firmware (Optional) - Uploads real-time data acquisition firmware to ESP32
2) Real-Time Streaming - Opens PyQt5 GUI with live ECG visualization and BLE data streaming; automatically stops after user-specified duration (can be stopped early by closing window or typing STOP). Saves raw packet data to CSV. 
3) Batch Processing - Processes collected data with R-peak detection algorithm.
4) Comparison Visualization - Generates overlay plots comparing real-time vs batch-processed results.
5) Metadata Logging - Saves recording details and user notes to text file.

## Customizing the Pipeline
- Sampling rate is currently fixed at 250hz (SAMPLING_RATE = 250); this is currently the only sampling rate frequency the frameworks support. Future additions will be added to the framework to allow for modifiable sampling rate. 

- Duration Range: To modify the 10-120 second constraint, edit lines 88-92 in stream_and_analyze_ecg_realtime.py:  
if user_dictated_duration < 10 or user_dictated_duration > 120:  # ← CHANGE THESE VALUES

*NOTE*: This pipeline uses BLE only for data transport to allow for freedom of movement during testing/use. Unlike pre-recorded testing pipelines, USB is not supported for real-time acquisition.  
Hardware Setup: Requires AD8232 sensor connected to ESP32 with live subject electrodes - refer to the [Collecting AD8232 Data for Pre-Recorded Testing](#collecting-ad8232-data-for-pre-recorded-testing) section for more details. 

---
## **Pre-Recorded Data Testing Framework**


## PhysioNet Validation Pipeline

### Quick Start

Run the complete PhysioNet validation pipeline:

```bash
python3 -m python.pre_recorded_testing_pipeline.master_controller_physionet
```
### User Prompts

The pipeline will interactively prompt you for:

**Patient ID**: Enter in format P##### (e.g., P00001)  
Validates that patient folder exists in datasets/PhysioNet Datasets/  
Re-prompts if folder not found  

**Segment ID**: Enter in format S## (e.g., s05)  
Validates that segment folder exists within patient folder  
Re-prompts if folder not found  

**Transport Method**: Enter USB or BLE  
Determines how ESP32 streams data to host  
USB: Wired serial connection (more reliable)  
BLE: Wireless Bluetooth (freedom of movement)  

**Example**:
What is the Patient ID you would like to test? ID should be entered in the format of P#####: P00001  
✅ Patient folder found: P00001  
What is the Segment ID you would like to test? ID should be entered in the format of S##: s05  
✅ Segment folder found: s05  
Would you like to test with USB streaming or BLE streaming? Please enter USB or BLE. BLE  
Accepted. Automated testing will be performed with streaming over BLE.  

### What It Does

Runs automated 5-step validation: dataset generation from pre-recorded PhysioNet data file → firmware flash → batch processing → real-time streaming → comparison plots.

See [Validation](VALIDATION.md) for detailed workflow explanation.

### Output Location

Results are saved to `data_logs/PhysioNet/{patient_id}_{segment_id}/{USB|BLE}/`

See [Output Files](OUTPUT_FILES.md) for CSV format details.

### Customizing the Pipeline

Dataset Selection: Patient ID and Segment ID are now entered via interactive prompts. No code editing required. 

Transport Method: USB or BLE is selected via interactive prompt during runtime.   

Time Window: To change the duration of data extracted from the PhysioNet file, edit line 134 in master_controller_physionet.py:  
digital_dataset, r_peaks, num_peaks, inst_bpms = generate_dataset_main(  
    file_name=file_name,  
    output_csv_path=output_dir,  
    bit_res=12,  
    start_s=0,    # Start time  
    end_s=15      # End time (seconds) ← CHANGE THIS  
)
Default: 15 seconds of ECG data  

---

## **AD8232 Hardware Validation Pipeline**

### Quick Start

Run the complete AD8232 validation pipeline:

```bash
python3 -m python.pre_recorded_testing_pipeline.master_controller_ad8232
```

### User Prompts

The pipeline will interactively prompt you for:  

**Dataset filename**: Enter the filename (without .csv extension)  
Example: ad8232_rest_run2_30_250  
Validates that file exists in datasets/AD8232 Data/  
Re-prompts if file not found  

**Transport Method**: Enter USB or BLE  
Determines how ESP32 streams data to host  

**Example**:  
What is the file name of the AD8232 pre-recorded dataset you would like to test?: ad8232_rest_run2_30_250  
AD8232 dataset found: ad8232_rest_run2_30_250.csv  
Would you like to test with USB streaming or BLE streaming? Please enter USB or BLE. USB  
Accepted. Automated testing will be performed with streaming over USB.  

### What It Does

Runs automated 5-step validation: dataset generation from pre-recorded AD8232 data → firmware flash → batch processing → real-time streaming → comparison plots.

See [Validation](VALIDATION.md#ad8232-hardware-validation-workflow) for detailed workflow explanation.


### Output Location

Results are saved to `data_logs/AD8232/{filename}/{USB|BLE}/`

See [Output Files](OUTPUT_FILES.md) for CSV format details.

### Customizing the Pipeline

Dataset Selection: Filename is now entered via interactive prompt (see above). No code editing required. 

Transport Method: USB or BLE is selected via interactive prompt during runtime. 

*NOTE*: The dataset file must already exist in datasets/AD8232 Data/. To create new datasets, use the real-time acquisition pipeline (see section below).

This will process the file:
```
datasets/AD8232 Datasets/ad8232_{CONDITION}_run{RUN_NUMBER}_{DURATION_SEC}_{SAMPLING_RATE}.csv
```

---

## **Individual Pipeline Steps (Pre-Recorded Testing)**

## Step 1: Generate Dataset
- python3 -m python.pre_recorded_testing_pipeline.step1_generate_dataset_physionet   # PhysioNet
- python3 -m python.pre_recorded_testing_pipeline.step1_generate_dataset_ad8232      # AD8232

## Step 2: Flash Firmware 
- python3 -m python.pre_recorded_testing_pipeline.step2_flash_firmware_usb    # USB version
- python3 -m python.pre_recorded_testing_pipeline.step2_flash_firmware_ble    # BLE version

## Step 3: Batch Processing
- python3 -m python.pre_recorded_testing_pipeline.step3_batchprocess

## Step 4: Real-Time Streaming
- python3 -m python.pre_recorded_testing_pipeline.step4_stream_usb [output_directory]   # USB
- python3 -m python.pre_recorded_testing_pipeline.step4_stream_ble [output_directory]   # BLE

## Step 5: Validation & Comparison
- python3 -m python.validation.compare_rpeak_bpm_physionet [output_directory]           # PhysioNet
- python3 -m python.validation.compare_rpeak_bpm_ad8232 [output_directory]              # AD8232


See [Validation](VALIDATION.md) for detailed explanations of what each step does.

---

## **Collecting AD8232 Data for Pre-Recorded Testing**

### Overview

You can collect custom AD8232 datasets under different conditions (rest, walking, post-exercise) using either USB (wired) or BLE (wireless) connection methods. Collected data is automatically saved to `datasets/AD8232 Data/` and can be used with the AD8232 validation pipeline.

### USB Collection Method

#### Firmware Required
Flash this firmware to ESP32 **before** running the collection script:
```
firmware/gateway/ad8232 data collection/stream_ad8232_data_usb.ino
```

#### Python Script
```bash
python3 -m python.hardware.collect_ad8232_data_usb
```

#### Configuration
Edit lines 52-56 in [python/hardware/collect_ad8232_data_usb.py](../python/hardware/collect_ad8232_data_usb.py):
```python
CONDITION = "rest"        # Test condition: "rest", "walk", "jog", "post_exercise"
RUN_NUMBER = 1            # Run identifier (1, 2, 3...)
DURATION_SEC = 30         # Recording duration in seconds
```

#### Hardware Setup
**GPIO Connections:**
- AD8232 OUTPUT → ESP32 GPIO 34 (analog input)
- AD8232 LO+ → ESP32 GPIO 13 (leads-off detection)
- AD8232 LO- → ESP32 GPIO 14 (leads-off detection)
- USB cable connected to host computer

**Electrode Placement:**
- RA (Right Arm): Right shoulder or upper chest
- LA (Left Arm): Left shoulder or upper chest
- RL (Right Leg): Lower right abdomen or hip (ground reference)

#### What It Does
1. Auto-detects ESP32 USB serial port
2. Sends START command to firmware
3. Collects ECG data at 250 Hz (4ms intervals)
4. Stops automatically when target sample count reached
5. Displays preview graph of collected data
6. Prompts user: **Save (Y) or Discard (N)**

#### Output Files
If saved, creates:
- **CSV file:** `datasets/AD8232 Data/ad8232_{CONDITION}_run{RUN}_{DURATION}_{250}.csv`
- **Graph:** `datasets/AD8232 Data/ad8232_{CONDITION}_run{RUN}_{DURATION}_{250}_graph.png`

**CSV Format:**
```
Raw_mV,Biased_V
-0.156,1.422
-0.142,1.436
```

---

### BLE Collection Method

#### Firmware Required
Flash this firmware to ESP32 **before** running the collection script:
```
firmware/gateway/ad8232 data collection/stream_ad8232_data_ble.ino
```

#### Python Script
```bash
python3 -m python.hardware.collect_ad8232_data_ble
```

#### Configuration
Edit lines 34-38 in [python/hardware/collect_ad8232_data_ble.py](../python/hardware/collect_ad8232_data_ble.py):
```python
CONDITION = "walk"        # Test condition
RUN_NUMBER = 1            # Run identifier
DURATION_SEC = 30         # Recording duration
```

#### Hardware Setup
**GPIO Connections:**
- Same as USB method (see above)
- **No USB cable required** - wireless BLE connection only
- Subject has full freedom of movement during data collection

#### What It Does
1. Scans for ESP32 BLE device ("ECG Monitor ESP32")
2. Connects wirelessly via Bluetooth Low Energy
3. Sends START command via BLE command characteristic
4. Receives binary data notifications (250 samples/packet = 500 bytes)
5. Stops automatically when target sample count reached
6. Displays preview graph
7. Prompts user: **Save (Y) or Discard (N)**

#### Output Files
Same format as USB method.

---

### Best Practices

**Test Condition Naming:**
- Use descriptive, consistent names: `rest`, `walk`, `jog`, `post_exercise`
- Avoid spaces or special characters

**Data Quality Review:**
- **Always review** the preview graph before saving
- Look for: clear QRS complexes, minimal noise, no flat-lining
- Discard (N) if data quality is poor, then re-collect

**Electrode Placement:**
- Ensure clean, dry skin contact
- Use adhesive electrodes or electrode gel for best results
- Check leads-off indicators (LO+/LO-) before starting

**NOTE**: Use **BLE** for recording a wider set of realistic movement scenarios (walking, jogging).

---

### Example Workflow

```bash
# 1. Collect resting baseline data (with BLE)
python3 -m python.hardware.collect_ad8232_data_ble
# Configure: CONDITION="rest", RUN_NUMBER=1, DURATION_SEC=30
# Review graph → Enter Y to save

# 2. Collect walking data (BLE - freedom of movement)
python3 -m python.hardware.collect_ad8232_data_ble
# Configure: CONDITION="walk", RUN_NUMBER=1, DURATION_SEC=30
# Walk around during collection → Review graph → Enter Y to save

# 3. Process the collected datasets
python3 -m python.pre_recorded_testing_pipeline.master_controller_ad8232
# Enter filename when prompted: ad8232_rest_run1_30_250
# Choose transport method: USB or BLE
```

---

## Configuration

### Global Configuration File

Edit `heartrate_config.json` for system-wide settings:

```json
{
    "type_of_data": "open-source",
    "open_source_time_s": 5,
    "bpm": 75,
    "sampling_hz": 250,
    "num_beats": 5,
    "heartbeat_type": "regular",
    "plot_window_s": 5
}
```

**Key Parameters:**
- `sampling_hz`: ADC sampling rate (250 Hz for AD8232)
- `plot_window_s`: Real-time visualization window

See complete parameter descriptions in [Installation](INSTALLATION.md#configuration).

### Serial Port Configuration

Edit python/pre_recorded_testing_pipeline/step4_stream_usb.py line 64:

```python
ser = serial.Serial("/dev/cu.usbserial-0001", 115200, timeout=1)
```

Find your port:
```bash
arduino-cli board list
# or
ls /dev/cu.*
```


---

## Next Steps

- Usage guide complete
- See [Validation](VALIDATION.md) for detailed workflow explanations
- See [Output Files](OUTPUT_FILES.md) for CSV format specifications

---

[← Back to Main README](../README.md) | [Documentation Index](DOCUMENTATION_INDEX.md)
