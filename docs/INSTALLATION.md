# Installation Guide

Complete setup instructions for the ECG Heart Rate Monitor validation framework.

> **Note**: These instructions are currently for the **ESP32 Dev** module and **macOS**. Installation requirements will vary for different OS and other models of the ESP32 system. 

## Quick Installation (Automated)

For a faster setup, you can use the automated installation script that handles virtual environment creation, dependency installation, and Arduino CLI setup:

```bash
# Run from project root directory
./INSTALLATION_SCRIPT.sh
```

The script will:
- Create and configure a Python virtual environment
- Install all required Python packages
- Set up Arduino CLI and ESP32 board support
- Verify the installation
- Create necessary project directories

**For manual installation or to understand each step in detail, continue reading below.**

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Hardware Requirements](#hardware-requirements)
- [Software Installation](#software-installation)
  - [Python Dependencies](#python-dependencies)
  - [Arduino CLI Setup](#arduino-cli-setup)
  - [Alternative: Arduino IDE](#alternative-arduino-ide)
- [Repository Setup](#repository-setup)
- [Dataset Setup](#dataset-setup)
- [ESP32 Firmware Setup](#esp32-firmware-setup)
- [Configuration](#configuration)
- [Verification](#verification)

---

## Prerequisites

Before installing, ensure you have:

- **Python 3.8+** installed
- **Git** for cloning the repository
- **USB cable** for ESP32 connection
- **ESP32 development board**
- (Optional) **AD8232 ECG sensor** for hardware data collection

---

## Hardware Requirements

### Current Validation Setup
- **ESP32 Development Board** - Acts as gateway/simulator for testing
- **USB Cable** - For serial communication with computer

### Final Target System
- **ESP32 Microcontroller**
- **AD8232 ECG Analog Front-End (AFE)**
- **Battery power supply**
- **ECG electrodes** (3 leads: RA, LA, RL)
- **WiFi connectivity** (built into ESP32)

---

## Software Installation

### Python Virtual Environment (Recommended)

**Why use a virtual environment?**

A virtual environment is strongly recommended for this project because it prevents conflicts with other Python projects on your system and guarantees you're using the exact package versions tested with this project. It also enables easy removal of project dependencies from your system (upon deletion of virtual environment).

**Create and activate virtual environment:**

```bash
# Navigate to project root
cd ECG-Monitor

# Create virtual environment
python3 -m venv ecg_venv

# Activate virtual environment
source ecg_venv/bin/activate  # macOS

# Your prompt should now show (ecg_venv)
```

**To deactivate later:**
```bash
deactivate
```

**Note:** You'll need to activate the virtual environment (`source ecg_venv/bin/activate`) each time you work on the project.

### Python Dependencies

**Install required packages:**
```bash
pip install -r requirements.txt
```

**Core packages installed:**
- `wfdb==4.3.0` - PhysioNet database access
- `numpy==2.1.3` - Numerical computing
- `scipy==1.16.1` - Signal processing (Butterworth filters)
- `matplotlib==3.10.1` - Static plotting
- `pandas==2.2.3` - CSV data manipulation
- `PyQt5==5.15.11` - GUI framework
- `pyqtgraph==0.13.7` - Real-time plotting
- `pyserial==3.5` - Serial communication with MCU

### Arduino CLI Setup

**Arduino CLI** is the recommended tool for automated firmware flashing.

#### Installation (Homebrew)

```bash
brew install arduino-cli
```

#### ESP32 Board Support Setup

```bash
# 1. Initialize Arduino CLI configuration
arduino-cli config init

# 2. Update board package index
arduino-cli core update-index

# 3. Add ESP32 board repository
arduino-cli config add board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json

# 4. Update index with ESP32 repository
arduino-cli core update-index

# 5. Install ESP32 core (may take several minutes)
arduino-cli core install esp32:esp32

# 6. Verify installation
arduino-cli board listall esp32
```

**Command purposes:**
- `config init`: Creates config file at `~/.arduino15/arduino-cli.yaml`
- `core update-index`: Downloads latest board package lists
- `config add board_manager.additional_urls`: Adds ESP32 repository
- `core install esp32:esp32`: Installs ESP32 compiler toolchain
- `board listall esp32`: Lists available ESP32 board variants

#### Identify Connected Board

```bash
# Connect ESP32 via USB, then run:
arduino-cli board list
```

**Expected output:**
```
Port                      Protocol  Type              Board Name  FQBN                    Core
/dev/cu.usbserial-0001   serial    Serial Port (USB)             esp32:esp32:esp32dev   esp32:esp32
```

Note the **Port** (e.g., `/dev/cu.usbserial-0001`) and **FQBN** (`esp32:esp32:esp32dev`) for later use.

### Alternative: Arduino IDE

If you prefer a GUI-based approach:

1. Download from [arduino.cc](https://www.arduino.cc/en/software)
2. Install ESP32 board support via **Tools → Board → Boards Manager**
3. Search for "ESP32" and install
4. Select your board: **Tools → Board → ESP32 Arduino → ESP32 Dev Module**

---

## Repository Setup

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/ECG-Monitor.git
cd ECG-Monitor
```

2. **Verify project structure:**
```bash
ls -la
# Should see: python/, firmware/, datasets/, docs/, etc.
```

---

## Dataset Setup

### PhysioNet Datasets

1. **Create datasets directory structure:**
```bash
mkdir -p "datasets/PhysioNet Datasets"
```

2. **Download ECG data** from [Icentia11k Database](https://physionet.org/content/icentia11k-continuous-ecg/1.0/):
```
datasets/
└── PhysioNet Datasets/
    └── ECG_Data_P00000/
        └── s00/
            ├── p00000_s00.dat    # Raw signal data
            ├── p00000_s00.hea    # Header file
            └── p00000_s00.atr    # Annotations (R-peaks)
```

### AD8232 Datasets

AD8232 datasets are stored in the `datasets/AD8232 Datasets/` folder:
```
datasets/
└── AD8232 Datasets/
    ├── ad8232_rest_run1_30_250.csv
    ├── ad8232_rest_run2_30_250.csv
    ├── ad8232_movement_run1_30_250.csv
    └── ad8232_post_exercise_run1_30_250.csv
```

---

## ESP32 Firmware Setup

### Using Arduino CLI (Recommended)

```bash
cd firmware/gateway

# Compile firmware
arduino-cli compile --fqbn esp32:esp32:esp32dev gateway.ino

# Upload to ESP32 (replace port with yours)
arduino-cli upload -p /dev/cu.usbserial-0001 --fqbn esp32:esp32:esp32dev gateway.ino
```

### Using Arduino IDE

1. Open `firmware/gateway/gateway.ino`
2. Select board: **Tools → Board → ESP32 Dev Module**
3. Select port: **Tools → Port → /dev/cu.usbserial-0001**
4. Click **Upload** button

---

## Configuration

### Validation Parameters

Edit `heartrate_config.json`:
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

**Parameters:**
- `type_of_data`: "open-source" for PhysioNet
- `open_source_time_s`: Duration to process (seconds)
- `sampling_hz`: ADC sampling rate (250 Hz for PhysioNet data and AD8232 data)
- `plot_window_s`: Real-time plot window

---

## Verification

### Test Python Environment

```bash
python3 -c "import wfdb, numpy, scipy, pandas, PyQt5, pyqtgraph, serial; print('All packages imported successfully')"
```

### Test Arduino CLI

```bash
arduino-cli version
arduino-cli board list
```

### Run Quick Test

```bash
# Test PhysioNet pipeline (requires dataset)
python3 -m python.pipeline.master_controller_physionet

# Or test AD8232 pipeline (requires hardware data)
python3 -m python.pipeline.master_controller_ad8232
```

---

## Next Steps

- Installation complete
- See [Usage Guide](USAGE.md) to run validation pipelines

---

[← Back to Main README](../README.md) | [Documentation Index](DOCUMENTATION_INDEX.md)
