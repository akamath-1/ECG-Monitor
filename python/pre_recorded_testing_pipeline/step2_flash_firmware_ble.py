import os
import subprocess
import serial
import serial.tools.list_ports
import time


class FirmwareGenerator:
    def __init__(
        self,
        fw_template_name="gateway_template_ble_version.ino",
        digital_dataset=None,
        file_id=None,
        values_per_line=15,
        fqbn="esp32:esp32:esp32",
    ):
        self.fw_template_name = fw_template_name
        self.digital_dataset = digital_dataset
        self.file_id = file_id
        self.values_per_line = values_per_line
        self.fqbn = fqbn
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

        firmware_dir = os.path.join(
            project_root, "firmware", "gateway", self.fw_template_name
        )

        self.fw_template_path = firmware_dir

    def generate_firmware_file(self):
        # create file path with firmware_template_name (os.join.path ?)
        # open firmware template file with file path
        # read firmware template as a STRING
        # locate empty array, replace it with {digital_dataset}

        # read firmware template:
        formatted_lines = []
        for entry in range(0, len(self.digital_dataset), self.values_per_line):
            digital_dataset_line = self.digital_dataset[
                entry : entry + self.values_per_line
            ]
            dig_dataset_line_string = [str(i) for i in digital_dataset_line]
            line = "  " + ", ".join(dig_dataset_line_string)

            # Add to lines list
            formatted_lines.append(line)
        formatted_digital_dataset = ",\n".join(formatted_lines)

        with open(self.fw_template_path, "r") as f:
            template_content = f.read()

        line_to_replace = "const uint16_t heartbeat_signal[] = {}"
        new_line = (
            f"const uint16_t heartbeat_signal[] = {{\n{formatted_digital_dataset}\n}}"
        )
        generated_firmware_content = template_content.replace(line_to_replace, new_line)

        if line_to_replace in generated_firmware_content:
            print("Dataset replacement failed! Firmware file contents not updated.")
            return None
        else:
            print("Dataset replacement successful!")

        # Build output directory and file paths
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        output_dir = os.path.join(
            project_root,
            "firmware",
            "gateway",
            "generated_firmware_files",
            f"gateway_ble_{self.file_id}",
        )
        output_filename = f"gateway_ble_{self.file_id}.ino"
        output_path = os.path.join(output_dir, output_filename)

        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Write generated firmware to new file
        with open(output_path, "w") as f:
            f.write(generated_firmware_content)

        # Confirmation
        print(f"✅ Generated BLE firmware file: {output_path}")
        print(f"   Dataset size: {len(self.digital_dataset)} samples")

        return output_path

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
def main(digital_dataset, file_id):
    """
    Generate BLE firmware file with embedded ECG dataset.

    Args:
        digital_dataset: List of ADC values (12-bit integers)
        file_id: Dataset identifier (e.g., "p00000_s00")

    Returns:
        None
    """

    # create instance of FirmwareGenerator
    generator = FirmwareGenerator(digital_dataset=digital_dataset, file_id=file_id)

    # generate firmware file and return firmware file path
    firmware_file_path = generator.generate_firmware_file()

    if firmware_file_path is None:
        print("Firmware file could not be generated.")
        return None
    # get firmware file path directory
    firmware_dir = os.path.dirname(firmware_file_path)
    # search for port and return found device

    print("Searching for port...")
    detected_port = generator.detect_port()

    if detected_port == None:
        print("Could not connect to ESP32. Cannot proceed, please try again.")
        return None

    # compile firmware
    print("Compiling firmware file...")
    compiled = generator.compile_firmware(firmware_dir)

    if not compiled:
        print("Compile failed, cannot go further.")
        return None

    # upload firmware
    print("Uploading firmware to ESP32...")
    uploaded = generator.upload_firmware(firmware_dir, port=detected_port)
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
    # Test mode disabled - use from master_controller
    pass
