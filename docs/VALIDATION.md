# Validation Framework

Detailed explanation of the ECG validation workflows and comparison methods.

---

## Table of Contents

- [Overview](#overview)
- [Usage](#usage)
- [PhysioNet Validation Workflow](#physionet-validation-workflow)
- [AD8232 Hardware Validation Workflow](#ad8232-hardware-validation-workflow)
- [Comparison Methods](#comparison-methods)
- [Results and Troubleshooting](#results-and-troubleshooting)

---

## Overview

This validation framework provides automated pipelines for testing R-peak detection and BPM calculation algorithms. It is designed to support iterative algorithm development by enabling quick validation cycles as new detection methods and improvements are added.

## Usage

**Communication Protocols**:
As of 12/7/25, both validation workflows (PhysioNet and AD8232) support testing over two communication interfaces:

USB/UART – Wired serial connection 
BLE – Wireless link for testing under motion and portable conditions

Supporting both protocols enables validation under both bench-top testing (USB/UART) and real-world movement scenarios (BLE: standing, walking, jogging). 

**Running the Pipeline**:
The files for these pipelines are located in ECG-Monitor/python/pre_recorded_testing_pipeline. Details for usage are included in [Usage Guide](USAGE.md). 

**Development approach:** Initial algorithm development and testing was performed using pre-recorded PhysioNet datasets, which provided access to diverse test subjects, heart rate conditions, and ground-truth annotations for validation. Once the core algorithm was established, development transitioned to testing with AD8232-collected data for more targeted optimization. Testing with data from the target hardware ensures the algorithm is robust under actual deployment conditions, accounting for hardware-specific characteristics like analog filtering, gain settings, and real-world noise that differ from clinical equipment.

This dual-validation approach allows thorough algorithm testing before final portable hardware deployment.


The framework provides two distinct workflows depending on the data source:

### PhysioNet Data: 3-Way Comparison
```
PhysioNet Dataset → [Annotated | Batch | Streamed] → Compare
```

**Three detection methods:**
- **Annotated**: Ground-truth R-peaks from clinical annotations
- **Batch**: Software detection on full dataset
- **Streamed**: Real-time detection via ESP32 

### AD8232 Hardware Data: 2-Way Comparison
```
AD8232 Recording → [Batch | Streamed] → Compare
```

**Two detection methods:**
- **Batch**: Software detection on recorded data
- **Streamed**: Real-time replay through ESP32

### Automated Firmware Flashing

The framework includes automated firmware generation and flashing to streamline the validation process. This automation:
- Reduces risk of manually miswriting datasets into firmware files
- Eliminates need to switch to Arduino IDE mid-pipeline
- Enables end-to-end testing without manual intervention

Users can still flash firmware manually using Arduino IDE if preferred.

---

## PhysioNet Validation Workflow

### Purpose

Validate algorithm accuracy against clinically-annotated ground truth from high-quality ECG recordings.

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                STEP 1: Generate Dataset                         │
│  • Parse PhysioNet WFDB files (*.dat, *.hea, *.atr)             │
│  • Extract ground-truth R-peaks from annotations                │
│  • Convert analog ECG (mV) → 12-bit digital ADC values          │
│  Output: annotated_outputs.csv, ECG Digital Dataset.csv         │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│              STEP 2: Flash Firmware                             │
│  • Generate firmware with embedded dataset                      │
│  • Compile and upload to ESP32                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
┌─────────▼──────────┐  ┌───────▼─────────────────────────────────┐
│ STEP 3: Batch      │  │    STEP 4: Real-Time Streaming          │
│   Processing       │  │  • ESP32 streams packets via USB        │
│  • SW R-peak       │  │  • Live R-peak detection & BPM          │
│    detection       │  │  • PyQt5 real-time visualization        │
│  • Full dataset    │  │  Output: streamed_data_outputs.csv      │
│  Output: batch_    │  └─────────┬───────────────────────────────┘
│    processed_      │            │
│    outputs.csv     │            │
└─────────┬──────────┘            │
          │                       │
          └───────────┬───────────┘
                      │
         ┌────────────▼────────────────────────────────────────────┐
         │        STEP 5: Validation & Comparison                  │
         │  • Generate overlay plots (ECG + R-peaks)               │
         │  • Compare BPM accuracy across all methods              │
         │  • Visual assessment against ground truth               │
         └─────────────────────────────────────────────────────────┘
```

### Step-by-Step Process

#### Step 1: Generate Dataset

**Input**: PhysioNet WFDB files
```
datasets/PhysioNet Datasets/ECG_Data_P00001/s05/
├── p00001_s05.dat    # Raw signal
├── p00001_s05.hea    # Header metadata
└── p00001_s05.atr    # Annotations (R-peaks)
```

**Process**:
1. Parse WFDB files using `wfdb` library
2. Extract R-peak annotations (ground truth)
3. Convert analog signal (mV) to 12-bit digital (0-4095)
4. Calculate instantaneous BPM from R-peak intervals

**Output**:
- `annotated_outputs.csv` - Ground-truth R-peaks with BPM
- `ECG Digital Dataset.csv` - Full digitized signal

#### Step 2: Flash Firmware

**Process**:
1. Generate `gateway.ino` with embedded digital dataset
2. Compile using Arduino CLI
3. Upload to ESP32 using Arduino CLI

**Purpose**: Load dataset into ESP32 flash memory for streaming validation.

#### Step 3: Batch Processing

**Process**:
1. Load digital dataset
2. Run R-peak detection algorithm
3. Calculate instantaneous BPM
4. Process entire dataset without real-time constraints

**Output**: `batch_processed_outputs.csv`

**Purpose**: Establish software-only baseline performance.

#### Step 4: Real-Time Streaming

**Process**:
1. ESP32 streams dataset in packets (10 samples @ 40ms intervals)
2. Host receives packets via serial
3. Real-time R-peak detection with 2-second calibration
4. Live visualization in PyQt5 GUI

**Output**:
- `streamed_raw_packets.csv` - All received packets
- `streamed_data_outputs.csv` - Detected R-peaks and BPM

**Purpose**: Validate algorithm under real-time constraints with packet timing.

#### Step 5: Comparison

**Process**:
1. Load all three output CSVs
2. Generate comparison plots:
   - Top: ECG signal with overlaid R-peaks (3 colors)
   - Bottom: Instantaneous BPM over time (3 lines)

**Purpose**: Visual assessment of detection accuracy against ground truth.

### What This Validates

1. **Algorithm accuracy** - Compare detected peaks vs. annotated ground truth
2. **Consistent behavior** - Batch and streaming should produce similar results
3. **Real-time performance** - Streaming validates timing and packet handling
4. **BPM calculation** - Verify heart rate calculations across all methods

---

## AD8232 Hardware Validation Workflow

### Purpose

Validate algorithm performance with actual hardware-collected ECG data under various physiological conditions.

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│           STEP 1: Convert Data to Digital Form                  │
│  • Load AD8232 CSV data                                         │
│  • Format for firmware embedding                                │
│  Output: Digital Dataset.txt                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│              STEP 2: Flash Firmware                             │
│  • Generate firmware with embedded dataset                      │
│  • Compile and upload to ESP32                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
┌─────────▼──────────┐  ┌───────▼─────────────────────────────────┐
│ STEP 3: Batch      │  │    STEP 4: Real-Time Streaming          │
│   Processing       │  │  • ESP32 streams packets via USB        │
│  • SW R-peak       │  │  • Live R-peak detection & BPM          │
│    detection       │  │  • PyQt5 real-time visualization        │
│  • Full dataset    │  │  Output: streamed_data_outputs.csv      │
│  Output: batch_    │  └─────────┬───────────────────────────────┘
│    processed_      │            │
│    outputs.csv     │            │
└─────────┬──────────┘            │
          │                       │
          └───────────┬───────────┘
                      │
         ┌────────────▼────────────────────────────────────────────┐
         │        STEP 5: Validation & Comparison                  │
         │  • Generate overlay plots (ECG + R-peaks)               │
         │  • Compare Batch vs Streamed BPM                        │
         │  • Visual calibration period marker                     │
         └─────────────────────────────────────────────────────────┘
```

### Step-by-Step Process

#### Step 1: Convert Data to Digital Form

**Input**: AD8232 CSV file
```
datasets/AD8232 Datasets/ad8232_rest_run2_30_250.csv
```

**Process**:
1. Load CSV data (already digitized from ADC)
2. Format for firmware array embedding

**Output**: `Digital Dataset.txt`

#### Step 2-4: Same as PhysioNet

Flash firmware, run batch processing, and stream data - identical to PhysioNet workflow.

#### Step 5: Comparison

**Process**:
1. Load batch and streamed CSVs
2. Generate comparison plots:
   - Top: ECG signal with overlaid R-peaks (batch=green, streamed=red)
   - Top: Purple dashed line at 500 samples (2-second calibration end)
   - Bottom: Instantaneous BPM over time (2 lines)
3. Remove first BPM entry (requires 2 peaks to calculate)

**Purpose**: Validate consistency between batch and real-time processing.

### What This Validates

1. **Hardware compatibility** - Algorithm works with AD8232 signal characteristics
2. **Robust under conditions** - Test with rest, movement, post-exercise
3. **Consistent behavior** - Batch and streaming produce similar results
4. **Real-world performance** - Validates with actual noise and artifacts

### Note About Analysis

AD8232 recordings don't have clinical annotations, so only **Batch** (software baseline) and **Streamed** (real-time) are compared.

Assumption: If batch and streamed results agree, the algorithm is working correctly. Differences indicate issues with real-time constraints or packet handling.

---

## Comparison Methods

### Visual Comparison

**Top Plot: ECG + R-Peaks**
- Shows where R-peaks were detected on the ECG signal
- **PhysioNet**: Green (annotated), Blue (batch), Red (streamed)
- **AD8232**: Green (batch), Red (streamed)
- Purple vertical line marks calibration period end

**Bottom Plot: Instantaneous BPM**
- Shows heart rate calculation over time
- Each point represents BPM calculated from the interval between consecutive R-peaks
- Allows visual assessment of BPM tracking accuracy

### Results and Troubleshooting

> **Note**: Formal tolerance thresholds for acceptable variation in BPM detection between annotated (when applicable), batch-processed, and real-time processed datasets are currently being developed. Current validation relies primarily on visual assessment. 

### Results should have:

- **R-peaks aligned** - All methods detect same peaks (no missed or false peaks)
- **BPM values close** - Generally within a few BPM across methods
- **Smooth BPM trend** - No erratic jumps
- **Consistent after calibration** - Stable detection of heart rate after 2 seconds

Automated testing will be later developed to statistically assess data for the above metrics. 

### Common Issues and Potential Causes

**Missed peaks** (gaps in detection):
- Threshold too high
- Signal quality issues
- Motion artifacts (AD8232)

**False peaks** (extra detections):
- Threshold too low
- Noise spikes
- T-wave detection (refractory period not long enough)

**BPM disagreement** (different values):
- Latency issues with real-time streaming
- Different RR-intervals used for calculation

**Calibration issues**:
- Threshold not properly established

---

## Other Documents

- → See [Usage Guide](USAGE.md) for running pipelines
- → See [Output Files](OUTPUT_FILES.md) for CSV format details

---

[← Back to Main README](../README.md) | [Documentation Index](DOCUMENTATION_INDEX.md)
