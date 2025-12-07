import os


def get_output_dir(patient_id: str, segment_id: str, connection_type: str) -> str:
    """
    Returns a consistent lowercase output directory for all CSVs/logs.
    Example: .../data_logs/p00000_s00
    """
    # Jump up to project root (ecg_monitor)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

    # Define base folder for all logs
    data_logs_dir = os.path.join(project_root, "data_logs", "PhysioNet")

    # Lowercase patient + segment combined
    output_folder = f"{patient_id.lower()}_{segment_id.lower()}"

    # Full path to this experiment's folder
    output_dir = os.path.join(data_logs_dir, output_folder, connection_type)

    # Make the directory if it doesn’t exist
    os.makedirs(output_dir, exist_ok=True)

    return output_dir
