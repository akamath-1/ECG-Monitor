# Changelog

All notable changes to this project will be documented in this file.

---

## Version 3.0 — 2025-12-07

### Overview
Functional prototype of ECG monitor with live signal acquisition, streaming, real-time analysis, and post-processing.

### Added
- Real-time data acquisition from AD8232
- Packetization on ESP32 and streaming to host
- Live beat-detection capability
- Offline post-processing pipeline for recorded data

### Changed
- Integrated previous frameworks (1. collecting cardiac signal data and 2. streaming pre-recorded ECG datasets from microcontroller to host device and analyzing it in real time) into a single end-to-end pipeline

### Notes / Limitations
- Prototype reliability varies under motion; signal quality and live beat detection need additional validation

### Next Steps
- Evaluate robustness across motion and noise conditions
- Implement design features as needed (i.e. in hardware, firmware, software) to reduce signal noise during movement

---

## Version 2.1 — 2025-12-06

### Overview
Expanded testing framework for beat-detection algorithm.

### Added
- BLE support for streaming pre-recorded datasets
- Testing harness for both PhysioNet and AD8232 datasets

### Changed
- Testing across two communication protocols (USB/UART and BLE)

### Notes / Limitations
- Focus remains on algorithm testing (for beat-detection accuracy, latency, etc. across communication protocols), rather than real-time ADC acquisition

---

## Version 2.0 — 2025-11-17

### Overview
Automated 5-step validation framework for beat detection using pre-recorded datasets.

### Added
- Data collection pipeline for AD8232 datasets
- Embedded dataset into firmware flash for 12-bit streaming
- On-board R-peak detection and BPM calculation

### Changed
- Simplified architecture from dual-ESP32 to single-ESP32 setup

### Notes / Limitations
- No real-time signal acquisition; ADC acquisition chain not validated
- Wired USB transmission restricts testing to stationary conditions

### Next Steps
- Integrate BLE data streaming to allow flexible dataset recording under motion

---

## Version 1.0 — 2025-11-06

### Overview
Initial two-ESP32 prototype used to simulate analog acquisition and packet streaming for validation.

### Added
- DAC → ADC chain to simulate analog ECG acquisition
- Packetization and USB streaming logic on Gateway MCU
- CSV-based post-streaming validation for data integrity

### Tested
- Packet integrity (header/footer markers: 0xAA, 0x55, 0xFF)
- Packet loss detection via sequential packet IDs
- Partial packet detection (validated complete 18-byte packets)
- Data integrity (transmitted vs received samples)
- Timing accuracy (consistent timestamps, 40 ms packet intervals)

### Notes / Limitations
- 8-bit resolution due to ESP32 DAC/ADC reduced signal quality
- Noise introduced by analog conversion degraded R-peak accuracy

### Next Steps
- Develop a 12-bit testing framework for improved algorithm validation

---
