#!/bin/bash
# Installation script for Control
# Sets up dependencies and directory structure

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo "Installing Control..."
echo "Base directory: $BASE_DIR"

# Create required directories
echo "Creating directories..."
mkdir -p "$BASE_DIR/config"
mkdir -p "$BASE_DIR/logs"
mkdir -p "$BASE_DIR/temp"
mkdir -p "$BASE_DIR/special"
mkdir -p "$BASE_DIR/recovery"
mkdir -p "$BASE_DIR/states/tiktok/home"
mkdir -p "$BASE_DIR/states/tiktok/upload"
mkdir -p "$BASE_DIR/interrupts/tiktok/update"
mkdir -p "$BASE_DIR/interrupts/system/update"

# Install Python dependencies
echo "Installing Python dependencies..."
python -m pip install -r "$BASE_DIR/requirements.txt"

# Download platform-tools if needed
PLATFORM_TOOLS_DIR="$BASE_DIR/platform-tools"
if [ ! -d "$PLATFORM_TOOLS_DIR" ]; then
    echo "Downloading Android platform-tools..."
    
    # Determine OS
    case "$(uname -s)" in
        Linux*)
            PLATFORM_TOOLS_URL="https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
            ;;
        Darwin*)
            PLATFORM_TOOLS_URL="https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
            ;;
        MINGW*|CYGWIN*|MSYS*)
            PLATFORM_TOOLS_URL="https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
            ;;
        *)
            echo "Unsupported operating system"
            exit 1
            ;;
    esac
    
    # Download and extract
    TEMP_ZIP="$BASE_DIR/temp/platform-tools.zip"
    curl -L "$PLATFORM_TOOLS_URL" -o "$TEMP_ZIP"
    unzip "$TEMP_ZIP" -d "$BASE_DIR"
    rm "$TEMP_ZIP"
    
    # Make ADB executable
    chmod +x "$PLATFORM_TOOLS_DIR/adb"
fi

# Copy example config if needed
CONFIG_FILE="$BASE_DIR/config/default_config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default configuration..."
    cp "$BASE_DIR/config/default_config.example.json" "$CONFIG_FILE"
fi

# Check for required environment variables
echo "Checking environment variables..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY environment variable not set"
    echo "Set this variable to enable recovery functionality"
fi
if [ -z "$GEMINI_API_KEY" ]; then
    echo "Warning: GEMINI_API_KEY environment variable not set"
    echo "Set this variable to enable recovery functionality"
fi

# Create Python package
echo "Creating Python package..."
cat > "$BASE_DIR/control/__init__.py" << EOL
"""
Control - Device Automation Agent
Version: 8.0.0
"""

from .config import Config, ConfigError
from .device_manager import DeviceManager, DeviceError
from .cloud_client import CloudClient, CloudError
from .workflow_executor import WorkflowExecutor, WorkflowError
from .screen_verifier import ScreenVerifier, ScreenError
from .special_handler import SpecialHandler, SpecialError
from .recovery_handler import RecoveryHandler, RecoveryError

__version__ = "8.0.0"
EOL

# Create startup script
echo "Creating startup script..."
cat > "$BASE_DIR/run.sh" << EOL
#!/bin/bash
# Start Control agent

# Get script directory
SCRIPT_DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment if it exists
if [ -d "\$SCRIPT_DIR/venv" ]; then
    source "\$SCRIPT_DIR/venv/bin/activate"
fi

# Start Control
python -m control "\$@"
EOL
chmod +x "$BASE_DIR/run.sh"

echo "Installation complete!"
echo
echo "To start Control:"
echo "1. Set required environment variables:"
echo "   export OPENAI_API_KEY=your_key_here"
echo "   export GEMINI_API_KEY=your_key_here"
echo
echo "2. Edit configuration in config/default_config.json"
echo
echo "3. Run the agent:"
echo "   ./run.sh"
echo
echo "Optional arguments:"
echo "  --config PATH    : Use alternative config file"
echo "  --debug         : Enable debug logging"
echo "  --no-cloud      : Run without Cloud connection"
