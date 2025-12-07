import os
import subprocess
import serial
import serial.tools.list_ports
import time


class FirmwareGenerator:
    def __init__(
        self,
        fw_template_name="real_time_streaming_ble.ino",
        fqbn="esp32:esp32:esp32",
    ):
        self.fw_template_name = fw_template_name

        self.fqbn = fqbn
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

        firmware_dir = os.path.join(
            project_root, "firmware", "gateway", self.fw_template_name
        )

        self.fw_template_path = firmware_dir

    def detect_port(self):
        ports = serial.tools.list_ports.comports()
        # ports.name = cu.usbserial-0001
        # ports.device = /dev/cu.usbserial-0001
        # ports.description = CP2102 USB to UART Bridge Controller
        keywords_description = ["usb", "serial", "ch340", "cp210", "ftdi"]
        for p in ports:
            if "usbserial" in p.device or any(
                keyword in p.description.lower() for keyword in keywords_description
            ):
                print(f"Found port: {p.device}")
                return p.device
        print("Error: Port not found.")
        return None

    def compile_firmware(self, firmware_dir):
        # cmd to compile firmware
        cmd = ["arduino-cli", "compile", "--fqbn", self.fqbn, firmware_dir]
        # result of attempt to compile firmware
        result = subprocess.run(cmd, capture_output=True, text=True)
        # capture_output = 0 for success, 1 for failure
        # text = error output (string)

        if result.returncode == 0:
            print("Compilation successful")
            return True
        else:
            print("Compilation failed:")
            print(result.stderr)
            return False

    def upload_firmware(self, firmware_dir=None, port=None):

        # for this command, the following information is needed: firmware file path,
        # port that MCU is connected to, and Fully Qualified Board Name (FQBN)

        # cmd = arduino-cli upload --fqbn self.fqbn --port port firmware_dir
        # cmd is what actually uploads the firmware to the boardr
        cmd = [
            "arduino-cli",
            "upload",
            "--fqbn",
            self.fqbn,
            "--port",
            port,
            "--verbose",  # Show detailed progress
            firmware_dir,
        ]  # create command string

        print("Starting upload (this may take 15-30 seconds)...")
        print(
            "If upload hangs, try pressing and holding the BOOT button (right of USB port) on the ESP32"
        )

        result = subprocess.run(
            cmd, text=True
        )  # run command and stream real-time updates of status
        # capture_output = 0 for success, 1 for failure
        # text = error output (string)
        if result.returncode == 0:
            print("Firmware uploaded successfully!")
            return True
        else:
            print(f"Upload failed. Reason for failure: {result.stderr}")
            return False


# Main function to be called from master_controller
def main():
    """
    Generate firmware file with embedded ECG dataset.

    Args:
        digital_dataset: List of ADC values (12-bit integers)
        file_id: Dataset identifier (e.g., "p00000_s00")

    Returns:
        None
    """

    # create instance of FirmwareGenerator
    generator = FirmwareGenerator()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    # get firmware file path directory
    firmware_dir = os.path.join(project_root, "firmware", "gateway")
    firmware_file_name = "real_time_streaming_ble"
    firmware_path = os.path.join(firmware_dir, firmware_file_name)

    # Verify firmware exists
    if not os.path.exists(firmware_path):
        print(f"ERROR: Firmware not found at {firmware_path}")
        return None

    # search for port and return found device

    print("Searching for port...")
    detected_port = generator.detect_port()

    if detected_port == None:
        print("Could not connect to ESP32. Cannot proceed, please try again.")
        return None

    # compile firmware
    print("Compiling firmware file...")
    compiled = generator.compile_firmware(firmware_path)

    if not compiled:
        print("Compile failed, cannot go further.")
        return None

    # upload firmware
    print("Uploading firmware to ESP32...")
    uploaded = generator.upload_firmware(firmware_path, port=detected_port)
    if not uploaded:
        print("Upload to ESP32 failed. Please try again.")
        return None

    # successful upload:
    print(
        "Firmware uploaded! Waiting for ESP32 to restart... please hit RESET button on ESP32 in the next four seconds to ensure successful upload."
    )
    time.sleep(4)
    return True


if __name__ == "__main__":
    main()
