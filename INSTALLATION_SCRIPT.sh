#!/bin/bash

################################################################################
# ECG Monitor - Automated Installation Script
################################################################################
#
# This script automates the setup of the ECG Heart Rate Monitor project by:
# 1. Creating a Python virtual environment
# 2. Installing all required Python dependencies
# 3. Setting up Arduino CLI for ESP32 firmware flashing
# 4. Configuring ESP32 board support
# 5. Verifying the installation
#
# Usage:
#   chmod +x ./INSTALLATION_SCRIPT.sh
#   ./INSTALLATION_SCRIPT.sh
#
# Requirements:
# - Python 3.8 or higher
# - Internet connection
# - macOS 
#
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if script is run from project root
if [ ! -f "requirements.txt" ] || [ ! -d "python" ]; then
    print_error "Error: This script must be run from the ECG-Monitor project root directory"
    echo "Current directory: $(pwd)"
    echo "Expected files: requirements.txt, python/, firmware/, etc."
    exit 1
fi

print_header "ECG Monitor - Automated Installation"
echo "This script will set up your development environment."
echo "Estimated time: 5-10 minutes (depending on internet speed)"
echo ""

# Step 1: Check Python version
print_header "Step 1/6: Checking Python Version"

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
print_success "Python $PYTHON_VERSION found"

# Check if version is 3.8+
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    print_error "Python 3.8 or higher is required. You have Python $PYTHON_VERSION"
    exit 1
fi

# Step 2: Create virtual environment
print_header "Step 2/6: Creating Virtual Environment"

VENV_DIR="ecg_venv"

if [ -d "$VENV_DIR" ]; then
    print_info "Virtual environment already exists at $VENV_DIR"
    read -p "Do you want to remove and recreate it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        print_info "Removed existing virtual environment"
    else
        print_info "Keeping existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created at $VENV_DIR"
else
    print_success "Using existing virtual environment"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
print_success "Virtual environment activated"

# Step 3: Upgrade pip
print_header "Step 3/6: Upgrading pip"

pip install --upgrade pip > /dev/null 2>&1
PIP_VERSION=$(pip --version | awk '{print $2}')
print_success "pip upgraded to version $PIP_VERSION"

# Step 4: Install Python dependencies
print_header "Step 4/6: Installing Python Dependencies"

if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found in project root"
    exit 1
fi

print_info "Installing packages from requirements.txt..."
pip install -r requirements.txt

print_success "Python dependencies installed successfully"

# List installed packages
print_info "Installed packages:"
pip list | grep -E "wfdb|numpy|scipy|pandas|PyQt5|pyqtgraph|pyserial|matplotlib"

# Step 5: Setup Arduino CLI
print_header "Step 5/6: Setting up Arduino CLI"

if command -v arduino-cli &> /dev/null; then
    ARDUINO_VERSION=$(arduino-cli version | head -n 1 | awk '{print $3}')
    print_success "Arduino CLI already installed (version $ARDUINO_VERSION)"
else
    print_info "Arduino CLI not found. Attempting to install via Homebrew..."

    if command -v brew &> /dev/null; then
        brew install arduino-cli
        print_success "Arduino CLI installed via Homebrew"
    else
        print_error "Homebrew not found. Please install Arduino CLI manually:"
        echo "  - macOS/Linux: curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh"
        echo "  - Or visit: https://arduino.github.io/arduino-cli/installation/"
        print_info "Skipping Arduino CLI setup for now..."
        SKIP_ARDUINO=true
    fi
fi

if [ "$SKIP_ARDUINO" != true ]; then
    # Initialize Arduino CLI
    print_info "Initializing Arduino CLI configuration..."
    arduino-cli config init > /dev/null 2>&1 || print_info "Config already exists"
    print_success "Arduino CLI configured"

    # Update board index
    print_info "Updating board package index..."
    arduino-cli core update-index
    print_success "Board index updated"

    # Add ESP32 board support
    print_info "Adding ESP32 board repository..."
    arduino-cli config add board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json > /dev/null 2>&1 || print_info "ESP32 URL already added"

    # Update index with ESP32
    arduino-cli core update-index

    # Check if ESP32 core is already installed
    if arduino-cli core list | grep -q "esp32:esp32"; then
        print_success "ESP32 core already installed"
    else
        print_info "Installing ESP32 core (this may take 5-10 minutes)..."
        arduino-cli core install esp32:esp32
        print_success "ESP32 core installed"
    fi
fi

# Step 6: Verify installation
print_header "Step 6/6: Verifying Installation"

# Test Python imports
print_info "Testing Python package imports..."
python3 -c "import wfdb, numpy, scipy, pandas, PyQt5, pyqtgraph, serial; print('All packages imported successfully')" 2>&1
if [ $? -eq 0 ]; then
    print_success "Python packages verified"
else
    print_error "Python package import failed"
fi

# Test Arduino CLI
if [ "$SKIP_ARDUINO" != true ]; then
    print_info "Testing Arduino CLI..."
    arduino-cli version > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        print_success "Arduino CLI verified"
    else
        print_error "Arduino CLI verification failed"
    fi

    # List available ESP32 boards
    print_info "Available ESP32 boards:"
    arduino-cli board listall esp32 | head -n 5
fi

# Check for connected boards
if [ "$SKIP_ARDUINO" != true ]; then
    print_info "Checking for connected ESP32 boards..."
    CONNECTED_BOARDS=$(arduino-cli board list | grep -c "esp32" || echo "0")
    if [ "$CONNECTED_BOARDS" -gt 0 ]; then
        print_success "ESP32 board detected"
        arduino-cli board list
    else
        print_info "No ESP32 boards currently connected (this is optional)"
    fi
fi

# Create directories if they don't exist
print_header "Creating Project Directories"

mkdir -p datasets/PhysioNet\ Datasets
mkdir -p datasets/AD8232\ Datasets
mkdir -p data_logs

print_success "Project directories created"

# Final summary
print_header "Installation Complete!"

echo "Summary:"
echo "  Python version: $PYTHON_VERSION"
echo "  Virtual environment: $VENV_DIR"
echo "  Python packages: Installed"
if [ "$SKIP_ARDUINO" != true ]; then
    echo "  Arduino CLI: Installed and configured"
    echo "  ESP32 support: Installed"
fi

echo ""
print_info "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source $VENV_DIR/bin/activate"
echo ""
echo "  2. (Optional) Download PhysioNet datasets:"
echo "     See docs/INSTALLATION.md for dataset setup instructions"
echo ""
echo "  3. Test Arduino CLI by flashing firmware to ESP32:"
echo "     You can test with either:"
echo ""
echo "     Option A - Gateway Template (for signal simulation):"
echo "       cd firmware/gateway"
echo "       arduino-cli compile --fqbn esp32:esp32:esp32dev gateway_template.ino"
echo "       arduino-cli upload -p /dev/cu.usbserial-XXXX --fqbn esp32:esp32:esp32dev gateway_template.ino"
echo ""
echo "     Option B - AD8232 Data Collection (for live ECG recording):"
echo "       cd firmware/gateway/ad8232\\ data\\ collection"
echo "       arduino-cli compile --fqbn esp32:esp32:esp32dev ad8232_data_collection.ino"
echo "       arduino-cli upload -p /dev/cu.usbserial-XXXX --fqbn esp32:esp32:esp32dev ad8232_data_collection.ino"
echo ""
echo "     (Replace /dev/cu.usbserial-XXXX with your actual port from 'arduino-cli board list')"
echo ""
echo "  4. Run validation pipeline:"
echo "     python3 -m python.pipeline.master_controller_physionet"
echo "     python3 -m python.pipeline.master_controller_ad8232"
echo ""
print_success "For detailed instructions, see docs/INSTALLATION.md"
echo ""
