# Control - Device Automation Agent

Control is a powerful automation agent for managing multiple Android devices. It provides a unified interface for device control, screen verification, workflow execution, and recovery handling.

## Architecture

Control is one of four main components of the SociaLlama system:

1. **Core**: Central logic center that handles:
   - Screen registry and verification
   - Workflow and sequence management
   - Analytics and scheduling
   - Recovery coordination

2. **Control**: Local agent installed on computers with connected phones
   - Device connection management
   - Screen verification
   - Action execution
   - Special sequence handling
   - Recovery execution

3. **Cloud**: Relay service for communication
   - Message routing between components
   - WebSocket connections
   - Binary file transfer
   - Connection management

4. **Connect**: Web interface for users
   - Device monitoring and control
   - Workflow creation and scheduling
   - Analytics and reporting
   - User management

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

3. Set required environment variables:
```bash
export OPENAI_API_KEY=your_key_here
export GEMINI_API_KEY=your_key_here
```

4. Edit configuration in `config/default_config.json`

5. Start the agent:
```bash
./run.sh
```

Optional arguments:
- `--config PATH`: Use alternative config file
- `--debug`: Enable debug logging
- `--no-cloud`: Run without Cloud connection

## Directory Structure

```
control/
├── config/                 # Configuration files
│   ├── default_config.json
│   └── default_config.example.json
├── control/               # Python package
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── device_manager.py
│   ├── cloud_client.py
│   ├── screen_verifier.py
│   ├── workflow_executor.py
│   ├── special_handler.py
│   └── recovery_handler.py
├── logs/                  # Log files
├── temp/                  # Temporary files
├── special/              # Special sequence scripts
├── recovery/             # Recovery scripts
├── states/               # Screen state references
│   └── tiktok/
│       ├── home/
│       └── upload/
├── interrupts/           # Interrupt screen references
│   ├── tiktok/
│   │   └── update/
│   └── system/
│       └── update/
├── platform-tools/       # Android platform tools
├── scripts/              # Installation and utility scripts
├── requirements.txt      # Python dependencies
└── run.sh               # Startup script
```

## Components

### Device Manager
- Manages device connections and reconnections
- Executes ADB commands
- Monitors device status
- Handles device configuration

### Screen Verifier
- Verifies current screen state
- Matches against known states and interrupts
- Handles validation regions
- Manages screen registry

### Workflow Executor
- Executes sequences and workflows
- Handles scheduling and dependencies
- Manages execution state
- Coordinates recovery attempts

### Special Handler
- Executes special sequences
- Manages sequence scripts
- Handles sequence parameters
- Reports execution results

### Recovery Handler
- Manages FarmCLI recovery attempts
- Handles API keys and scripts
- Coordinates recovery process
- Reports recovery status

### Cloud Client
- Maintains WebSocket connection
- Handles message routing
- Manages binary transfers
- Reconnects automatically

## Configuration

The system is configured through `config/default_config.json`. Key settings include:

- Cloud connection parameters
- Device check intervals
- Workflow execution settings
- Recovery attempt limits
- Screen verification thresholds
- Debug options
- Device definitions
- Screen state definitions
- Interrupt definitions

See `config/default_config.example.json` for a complete example.

## Development

1. Set up development environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

2. Install development tools:
```bash
pip install black isort flake8 mypy pytest
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

5. Run linters:
```bash
flake8 control/
mypy control/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linters
5. Submit a pull request

## License

Copyright © 2025 Your Company. All rights reserved.
