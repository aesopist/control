# Control - Device Automation Agent

Control is a robust automation agent for managing and executing operations on multiple Android devices. It serves as the execution layer that interacts directly with connected phones via ADB, executing workflows, verifying screens, and reporting results back to Cloud.

## System Architecture

Control is part of a larger automation platform with four main components:

1. **Control**: This component (contained in this repository), which executes operations on physical devices
2. **Cloud**: A relay service that handles communication between components
3. **Core**: The central intelligence and decision-making component
4. **Connect**: The user interface for monitoring and interacting with the system

Control communicates exclusively with Cloud, acting as a thin execution layer that receives packages, executes them on devices, and reports results back.

## Core Functionality

Control's main responsibilities include:

1. **Device Management**
   - Maintaining ADB connections to physical phones
   - Executing ADB commands on devices
   - Monitoring device connectivity and handling reconnections

2. **Workflow Execution**
   - Executing pre-defined workflow packages received from Cloud
   - Executing sequences and individual steps on devices
   - Reporting execution progress and results

3. **Screen Verification**
   - Capturing screenshots from devices
   - Comparing screenshots against reference images
   - Identifying unknown screens and reporting them to Cloud

4. **Special Sequence Handling**
   - Executing injected code for complex operations securely
   - Providing environment for special sequences and recovery scripts
   - Isolating execution to prevent security issues

5. **Package Management**
   - Receiving encrypted packages from Cloud
   - Extracting and managing workflow data and media files
   - Cleaning up temporary files after execution

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/control.git
cd control
```

2. Run the installation script:
```bash
./scripts/install.sh
```

3. Set up configuration:
```bash
cp config/default_config.example.json config/default_config.json
# Edit configuration as needed
```

4. Start Control:
```bash
./run.sh
```

### Optional Arguments
- `--config PATH`: Use an alternative configuration file
- `--debug`: Enable debug logging
- `--local`: Use local compute for development instead of Cloud

## Directory Structure

```
control/
├── README.md                   # Documentation
├── requirements.txt            # Python dependencies
├── setup.py                    # Installation script
├── run.sh                      # Startup script
├── control/                    # Main package
│   ├── __init__.py             # Package initialization
│   ├── __main__.py             # Entry point
│   ├── config.py               # Configuration management
│   ├── device_manager/         # Device connection management
│   │   ├── __init__.py
│   │   ├── connection.py       # Device connection handling
│   │   ├── command.py          # Device command execution
│   │   └── monitor.py          # Connection monitoring
│   ├── verification/           # Screen verification
│   │   ├── __init__.py
│   │   ├── verifier.py         # Screen verification logic
│   │   ├── comparator.py       # Image comparison
│   │   └── registry.py         # Screen registry management
│   ├── cloud/                  # Cloud communication
│   │   ├── __init__.py
│   │   ├── client.py           # WebSocket client
│   │   ├── protocol.py         # Message protocol definitions
│   │   └── binary.py           # Binary data handling
│   ├── workflows/              # Workflow execution
│   │   ├── __init__.py
│   │   ├── executor.py         # Workflow execution
│   │   ├── sequence.py         # Sequence handling
│   │   └── step.py             # Step execution
│   ├── sandbox/                # Secure code execution
│   │   ├── __init__.py
│   │   └── runner.py           # Special sequence and recovery execution
│   ├── keyboard/               # Keyboard integration
│   │   ├── __init__.py
│   │   ├── client.py           # Keyboard client
│   │   └── sequence.py         # Keyboard sequence builder
│   └── utils/                  # Utilities
│       ├── __init__.py
│       └── logging.py          # Logging utilities
├── scripts/                    # Installation scripts
│   ├── install.sh              # Main installation script
│   └── download_platform_tools.sh # ADB download script
├── config/                     # Configuration files
│   ├── default_config.json     # Default configuration
│   └── default_config.example.json # Example configuration
├── logs/                       # Log directory
├── platform-tools/             # Android platform tools
└── temp/                       # Temporary file storage
    ├── workflows/              # Workflow temporary files
    ├── screenshots/            # Screenshot temporary files
    └── sandbox/                # Sandbox temporary files
```

## Key Components

### Device Manager
Handles device connections, command execution, and monitoring device connectivity. This includes:
- Discovering and connecting to devices via ADB
- Executing commands on devices (tap, swipe, key events)
- Monitoring device connectivity and handling reconnections
- Capturing screenshots from devices

### Screen Verification
Handles verification of device screens against reference images:
- Comparing captured screenshots to reference images
- Identifying screen state based on validation regions
- Finding best match when expected screen isn't encountered
- Reporting unknown screens to Cloud for further processing

### Cloud Client
Handles WebSocket communication with Cloud relay:
- Maintaining persistent WebSocket connection
- Handling protocol message serialization/deserialization
- Managing binary data transfers (screenshots, media files)
- Reconnecting automatically when connection is lost

### Workflow Executor
Manages execution of workflows received from Cloud:
- Processing workflow packages
- Executing sequences and steps on devices
- Verifying screen states during execution
- Reporting execution progress and results back to Cloud

### Sandbox Runner
Provides secure execution environment for injected code:
- Running special sequences in isolated environment
- Executing recovery scripts with proper security boundaries
- Managing execution timeout and resource constraints
- Cleaning up after execution completes

### Keyboard Client
Handles communication with the custom keyboard app:
- Sending text input commands
- Managing clipboard operations
- Executing keyboard sequences (typing, dictation, autofill)

## Package Structure

Workflow packages sent to Control follow this general structure:

```json
{
  "package_type": "workflow",
  "package_id": "unique_identifier",
  "workflow": {
    "workflow_id": "workflow_unique_id",
    "name": "Workflow Name",
    "sequences": [
      {
        "sequence_id": "sequence_unique_id",
        "name": "Sequence Name",
        "steps": [
          {
            "step_id": "step_unique_id",
            "type": "tap",
            "coordinates": [540, 960],
            "expected_screen_after": "screen_id_1"
          }
        ]
      }
    ]
  },
  "screen_registry": {
    "screen_id_1": {
      "name": "Screen Name",
      "image": "screen_id_1.png",
      "validation_regions": [
        {"x1": 100, "y1": 200, "x2": 300, "y2": 400}
      ]
    }
  },
  "device_id": "192.168.1.101:5555"
}
```

## Configuration

Control is configured through a JSON configuration file (`config/default_config.json`). Important configuration options include:

- `cloud.url`: WebSocket URL for Cloud relay
- `cloud.reconnect_interval`: Time between reconnection attempts
- `workflow.verification_timeout`: Maximum time to wait for screen verification
- `devices`: Device configuration including friendly names and IP addresses

## Development

### Setting Up Development Environment

1. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install development dependencies:
```bash
pip install -e .
pip install pytest black isort flake8
```

3. Run tests:
```bash
pytest
```

4. Format code:
```bash
black control/
isort control/
```

### Adding New Functionality

To add new functionality to Control:

1. **Device Commands**: Add methods to `device_manager/command.py`
2. **Screen Verification**: Enhance verification logic in `verification/verifier.py`
3. **Protocol Messages**: Add message types in `cloud/protocol.py`
4. **Workflow Execution**: Add execution logic in `workflows/` modules

## Troubleshooting

Common issues and their solutions:

1. **Device Connection Issues**
   - Ensure USB debugging is enabled on the device
   - Check ADB server is running: `adb start-server`
   - Try connecting via USB before WiFi
   - Verify device IP address in configuration

2. **Screen Verification Failures**
   - Check that reference images are up to date
   - Verify validation regions are properly defined
   - Check for UI changes in the app

3. **Workflow Execution Errors**
   - Verify workflow package structure
   - Check device connectivity
   - Review logs for specific error messages
   - Look for unknown screens

## License

Copyright © 2025 Your Company. All rights reserved.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request
