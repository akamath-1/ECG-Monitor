"""
AD8232 Data Comparison Tool
Compares batch-processed vs real-time streamed data for AD8232 ECG datasets.

Format for Batch Processed Outputs:
Detected R_peak_index,Digital Value,Instantaneous_BPM

Format for Streamed Data Outputs:
Detected R_peak_index,Digital Value,Instantaneous_BPM

This script mirrors the plot_all() function from compare_csv_data_rpeak_bpm.py
but only compares batch vs streamed data (no annotated PhysioNet data).
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sys


def plot_all(csv_log_folder_path, save_path=None):
    """
    Create a 2-subplot comparison plot:
    - Top: ECG signal with R-peaks overlaid (batch vs streamed)
    - Bottom: BPM comparison over time (batch vs streamed)

    Args:
        csv_log_folder_path: Path to folder containing the CSV files
        save_path: Optional path to save the figure. If None, figure is only displayed.
    """
    fig, axs = plt.subplots(2, 1, figsize=(14, 10), sharex=False)

    # === Load batch and streamed data ===
    batch_path = os.path.join(csv_log_folder_path, "batch_processed_outputs.csv")
    streamed_path = os.path.join(csv_log_folder_path, "streamed_data_outputs.csv")

    batch = pd.read_csv(batch_path)
    streamed = pd.read_csv(streamed_path)

    # Remove first BPM entry from both datasets (first peak has no BPM calculation)
    if len(batch) > 0:
        batch = batch.iloc[1:].reset_index(drop=True)
    if len(streamed) > 0:
        streamed = streamed.iloc[1:].reset_index(drop=True)

    # === Load ECG digital dataset ===
    # Try AD8232 naming convention first, then PhysioNet convention
    digital_dataset_path = os.path.join(csv_log_folder_path, "Digital Dataset.txt")
    if not os.path.exists(digital_dataset_path):
        digital_dataset_path = os.path.join(csv_log_folder_path, "Digital Dataset.txt")

    ecg_digital = pd.read_csv(digital_dataset_path, header=None).squeeze()

    # --- Top: ECG + R-peaks ---
    axs[0].plot(ecg_digital, color="blue", label="ECG Signal")
    axs[0].scatter(
        batch["Detected R_peak_index"],
        batch["Digital Value"],
        color="green",
        s=50,
        label="Batch",
    )
    axs[0].scatter(
        streamed["Detected R_peak_index"],
        streamed["Digital Value"],
        color="red",
        s=50,
        label="Streamed",
    )

    # Add calibration period vertical line
    # Calibration period: 2 seconds at 250 Hz = 500 samples
    calibration_samples = 2 * 250  # sec_of_calibration * sampling_rate
    axs[0].axvline(
        x=calibration_samples,
        color="purple",
        linestyle="--",
        linewidth=2,
        label="Calibration End (2s)",
    )

    axs[0].set_ylabel("ADC Value")
    axs[0].set_title("R-Peak Detection Comparison")
    axs[0].legend()
    axs[0].grid(True)

    # --- Bottom: BPM vs R-peak index ---
    axs[1].plot(
        batch["Detected R_peak_index"],
        batch["Instantaneous_BPM"],
        color="green",
        marker="o",
        label="Batch",
    )
    axs[1].plot(
        streamed["Detected R_peak_index"],
        streamed["Instantaneous_BPM"],
        color="red",
        marker="x",
        label="Streamed",
    )
    axs[1].set_xlabel("R-Peak Index (Sample Number)")
    axs[1].set_ylabel("Instantaneous BPM")
    axs[1].set_title("BPM Comparison")
    axs[1].legend()
    axs[1].grid(True)

    plt.tight_layout()

    # Save figure if path provided
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Comparison plot saved to: {save_path}")

    plt.show()


def main(csv_logs_folder_path, save_path=None):
    """
    Main function to run comparison plots.

    Args:
        csv_logs_folder_path: Path to folder containing CSV files
        save_path: Optional path to save the comparison plot
    """
    plot_all(csv_logs_folder_path, save_path=save_path)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_logs_folder_path = sys.argv[1]
    else:
        # For testing - replace with your actual path
        csv_logs_folder_path = "/Users/anuyakamath/Desktop/ECG-Monitor-GitHub/ECG-Monitor/data_logs/default_run"
        # this data is the same data as is generated from rest_run2_30_250
    main(csv_logs_folder_path)
