# Usage Guide

How to run the ECG Heart Rate Monitor validation pipelines.

> **Note**: This guide currently covers how to run the validation pipeline for algorithm testing. It will be expanded in future updates to include instructions for real-time ECG acquisition and wireless data transmission once those features are implemented.

---

## Table of Contents

- [Overview](#overview)
- [PhysioNet Validation Pipeline](#physionet-validation-pipeline)
- [AD8232 Hardware Validation Pipeline](#ad8232-hardware-validation-pipeline)
- [Individual Pipeline Steps](#individual-pipeline-steps)
- [Configuration](#configuration)

---

## Overview

The validation framework provides two main pipelines:

1. **PhysioNet Pipeline** - Validates algorithm against clinical datasets with ground-truth annotations
2. **AD8232 Pipeline** - Validates algorithm with hardware-collected ECG data

Both pipelines automate the entire validation workflow from data processing to comparison visualization.

---

## PhysioNet Validation Pipeline

### Quick Start

Run the complete PhysioNet validation pipeline:

```bash
python3 -m python.pipeline.master_controller_physionet
```

### What It Does

Runs automated 5-step validation: dataset generation from pre-recorded PhysioNet data file → firmware flash → batch processing → real-time streaming → comparison plots.

See [Validation](VALIDATION.md#physionet-validation-workflow) for detailed workflow explanation.

### Output Location

Results are saved to `data_logs/{patient_id}_{segment_id}/`

See [Output Files](OUTPUT_FILES.md) for CSV format details.

### Customizing the Pipeline

To customize the parameters `python/pipeline/master_controller_physionet.py`, change:

```python
patient_id = "P00001"     # PhysioNet patient ID
segment_id = "s05"        # Segment to process
```

And configure time window in the `generate_dataset_main()` call:

```python
digital_dataset, r_peaks, num_peaks, inst_bpms = generate_dataset_main(
    file_name=file_name,
    output_csv_path=output_dir,
    bit_res=12,
    start_s=0,    # Start time
    end_s=15      # End time (seconds)
)
```

---

## AD8232 Hardware Validation Pipeline

### Quick Start

Run the complete AD8232 validation pipeline:

```bash
python3 -m python.pipeline.master_controller_ad8232
```

### What It Does

Runs automated 5-step validation: dataset generation from pre-recorded AD8232 data → firmware flash → batch processing → real-time streaming → comparison plots.

See [Validation](VALIDATION.md#ad8232-hardware-validation-workflow) for detailed workflow explanation.

### Output Location

Results are saved to `data_logs/AD8232/{filename}/`

See [Output Files](OUTPUT_FILES.md) for CSV format details.

### Customizing the Pipeline

Edit `python/pipeline/master_controller_ad8232.py` to configure:

```python
CONDITION = "rest"              # or "movement", "post_exercise"
RUN_NUMBER = 2                  # Run identifier
DURATION_SEC = 30               # Recording duration
SAMPLING_RATE = 250             # Sampling frequency
```

This will process the file:
```
datasets/AD8232 Datasets/ad8232_{CONDITION}_run{RUN_NUMBER}_{DURATION_SEC}_{SAMPLING_RATE}.csv
```

---

## Individual Pipeline Steps

You can run pipeline steps individually for debugging or development:

```bash
# Step 1: Generate Dataset
python3 -m python.pipeline.step1_generate_dataset_physionet             # PhysioNet
python3 -m python.pipeline.step1_generate_dataset_ad8232       # AD8232

# Step 2: Flash Firmware (automatically called by master controllers)
python3 -m python.pipeline.step2_flash_firmware

# Step 3: Batch Processing
python3 -m python.pipeline.step3_batchprocess

# Step 4: Real-Time Streaming
python3 -m python.pipeline.step4_stream [output_directory]

# Step 5: Validation & Comparison
python3 -m python.validation.compare_rpeak_bpm_physionet [output_directory]           # PhysioNet
python3 -m python.validation.compare_rpeak_bpm_ad8232 [output_directory]       # AD8232
```

See [Validation](VALIDATION.md) for detailed explanations of what each step does.

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

Edit `python/pipeline/step4_stream.py` line 64:

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

## Common Workflows

### Test Algorithm on New PhysioNet Data

1. Download dataset to `datasets/PhysioNet Datasets/`
2. Edit patient/segment in `master_controller_physionet.py`
3. Run: `python3 -m python.pipeline.master_controller_physionet`

### Test Algorithm on New AD8232 Data

1. Place CSV in `datasets/AD8232 Datasets/`
2. Edit configuration in `master_controller_ad8232.py`
3. Run: `python3 -m python.pipeline.master_controller_ad8232`

### Quick Comparison Without Re-running Pipeline

If you've already run the pipeline:

```bash
# PhysioNet
python3 -m python.validation.compare_rpeak_bpm_physionet data_logs/p00001_s05

# AD8232
python3 -m python.validation.compare_rpeak_bpm_ad8232 data_logs/AD8232/ad8232_rest_run2_30_250
```

---

## Next Steps

- Usage guide complete
- See [Validation](VALIDATION.md) for detailed workflow explanations
- See [Output Files](OUTPUT_FILES.md) for CSV format specifications

---

[← Back to Main README](../README.md) | [Documentation Index](DOCUMENTATION_INDEX.md)
