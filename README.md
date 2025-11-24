# ECG Heart Rate Monitor
# About this Project


This project focuses on developing portable, battery-operated heart rate monitor using an ESP32 and AD8232 ECG analog front-end (AFE) for real-time cardiac health and fitness monitoring.

I started this project to create a portable and accessible cardiac monitor that could be used to as a supplemental tool to assess cardiac health. As a consumer of few different biowearable products myself, I have gained valuable insight regarding my health from using these technologies in my day-to-day life. The field of biowearables holds so much promise to enable consumers to make more informed decisions about health management, and I am constantly inspired by the technologies that others are developing in this field. However, commercially available biowearable products can be highly priced and difficult to modify or extend, and I wanted to challenge myself to see what I could create with easily sourceable, off-the-shelf components and open-source code. I have outlined below what I have created so far, and will continue to add new features and learnings to this repository as I further develop this monitoring system. 

[![Project Status](https://img.shields.io/badge/status-active%20development-green)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

---

## Project Goals

So far, I have developed a system that: 
- Acquires ECG signals using the AD8232 analog front-end 
- Processes data in the firmware of an ESP32 microcontroller and streams the data to a host device via a USB-UART serial interface
- Implements back-end software to receive the streamed data and further process it for analysis (additional details below) 

Currently, I am implementing features to:
- Integrate the AD8232 into the pipeline for *both* live signal acquisition and processing
- Wirelessly stream collect signal data from the ESP32 to a host device via BLE or Wi-Fi
- Power the system via battery

Future steps will include:
- Advancing the beat-detection algorithm to better handle signal noise and detect abornmalities and deviations in heart rate 
- Integrating test protocols that can be used to assess cardiac fitness


I have included further detail below about the current capabilities of this ECG monitor system (i.e beat-detection algorithm, data processing and validation methods, etc.), as well instructions for how to get started with building and deploying this system.

## Current Status

## Key Features

Currently, this repository contains a **validation and testing framework** for ECG signal processing algorithms. The framework is designed to process two pre-recorded sources of ECG data: open-source ECG data available from PhysioNet's database*, and ECG data collected via the AD8232-ESP32 module. It implements the following key features:

- **Multi-source validation** - Compares the peaks and BPM values calculated from batch-processed ECG data and real-time streaming (as well ground-truth annotations when applicable) to verify algorithm consistency across processing methods
- **Real-time visualization** - Live ECG plotting with PyQt5/pyqtgraph
- **Pan-Tompkins algorithm** - Calculation method for R-peak detection
- **Data logging** - CSV outputs for all processing stages

### Hardware Testing
- **Hardware-in-the-loop** - Test firmware with real physiological data collected under various test conditions (rest, movement, post-exercise)
- **Heart rate monitoring** - Instantaneous and windowed BPM calculation
- **Automated comparison** - Validation of results of batch-processed data vs. data processed in real-time


*Note: PhysioNet ECG datasets include a source of ground-truth annotations, which are parsed and included in post-processing analysis of ECG data. Datasets collected with the AD8232-ESP32 module do not have this annotation. Further details about development approach and data validation processes are included in the [**Validation Guide**](docs/VALIDATION.md) section of the repository. 


**Work in progress:** I am now working on transitioning to wireless data transmission and battery power for the system. The elimination of cable usage will increase portability and allow me to flexibly collect ECG datasets under various physiological conditions (rest, movement, post-exercise), which can then be used to further optimize the beat-detection algorithm (i.e. enhancing filtering, drift detection, specifically tailored to data collected from the AD8232 AFE). 

---



## Documentation

### Getting Started
- [Installation Guide](docs/INSTALLATION.md) - Dependencies, Arduino CLI setup, ESP32 configuration
- [Usage Guide](docs/USAGE.md) - Running pipelines, individual steps, configuration
- [Project Structure](docs/PROJECT_STRUCTURE.md) - Overview of project files and structure

### Technical Details
- [Validation Framework](docs/VALIDATION.md) - PhysioNet vs AD8232 workflows, comparison methods
- [Output Files](docs/OUTPUT_FILES.md) - CSV formats, data structure
- [Algorithm Details](docs/ALGORITHM.md) - R-peak detection, BPM calculation, parameters (coming soon)
- [Hardware Setup](docs/HARDWARE_SETUP.md) - ESP32, AD8232, sensor placement (coming soon)

### Development
- [Development Roadmap](docs/ROADMAP.md) - Planned features and milestones

---

## Disclaimer

This system (including all hardware designs, software, and documentation) is a research and educational prototype only. It is **not a medical device** and should **not be used for diagnostic or clinical purposes**.

---

## Acknowledgments

**PhysioNet** - Open-access ECG databases:
- Tan, S., Ortiz-Gagné, S., Beaudoin-Gagnon, N., Fecteau, P., Courville, A., Bengio, Y., & Cohen, J. P. (2022). Icentia11k Single Lead Continuous Raw Electrocardiogram Dataset (version 1.0). PhysioNet. RRID:SCR_007345. https://doi.org/10.13026/kk0v-r952
- Original publication: Tan, S., Androz, G., Ortiz-Gagné, S., Chamseddine, A., Fecteau, P., Courville, A., Bengio, Y., & Cohen, J. P. (2021, October 21). Icentia11K: An Unsupervised Representation Learning Dataset for Arrhythmia Subtype Discovery. Computing in Cardiology Conference (CinC).
- Goldberger, A., Amaral, L., Glass, L., Hausdorff, J., Ivanov, P. C., Mark, R., ... & Stanley, H. E. (2000). PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. Circulation [Online]. 101 (23), pp. e215–e220. RRID:SCR_007345.

You can find the full dataset on [PhysioNet](https://physionet.org/content/icentia11k-continuous-ecg/1.0/#files-panel).

**Pan & Tompkins** - Classic QRS detection algorithm (1985)
- J. Pan and W. J. Tompkins, "A Real-Time QRS Detection Algorithm," in IEEE Transactions on Biomedical Engineering, vol. BME-32, no. 3, pp. 230-236, March 1985, doi: 10.1109/TBME.1985.325532.

**wfdb-python** - [PhysioNet data access library](https://github.com/MIT-LCP/wfdb-python)

---

## Contact

For questions or issues, please [open an issue](https://github.com/yourusername/ECG-Monitor/issues) on GitHub.

---

**Status**: Active development | Algorithm validation framework operational | Hardware integration in progress
