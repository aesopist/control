# Control Component File Structure

Based on our discussions and the package structure we've defined, here's a comprehensive file structure for the Control component:

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
│   ├── device_manager.py       # Device connection management
│   │   ├── __init__.py
│   │   ├── connection.py       # ADB connection handling
│   │   ├── command.py          # Device command execution
│   │   └── monitor.py          # Connection monitoring
│   ├── actions/                # Action execution
│   │   ├── __init__.py
│   │   ├── base.py             # Base action class
│   │   ├── tap.py              # Tap execution
│   │   ├── swipe.py            # Swipe execution
│   │   ├── text.py             # Text input (keyboard)
│   │   └── special.py          # Special action handling
│   ├── keyboard/               # Keyboard integration
│   │   ├── __init__.py
│   │   ├── client.py           # Keyboard client
│   │   └── sequence.py         # Sequence execution
│   ├── verification/           # Screen verification
│   │   ├── __init__.py
│   │   ├── verifier.py         # Main verification logic
│   │   ├── comparator.py       # Image comparison
│   │   └── registry.py         # Local registry management
│   ├── cloud/                  # Cloud communication
│   │   ├── __init__.py
│   │   ├── client.py           # WebSocket client
│   │   ├── protocol.py         # Message protocol
│   │   └── binary.py           # Binary data handling
│   ├── workflows/              # Workflow execution
│   │   ├── __init__.py
│   │   ├── executor.py         # Workflow execution
│   │   ├── sequence.py         # Sequence handling
│   │   └── step.py             # Step execution
│   ├── sandbox/                # Code execution sandbox
│   │   ├── __init__.py
│   │   ├── runner.py           # Code execution
│   │   └── security.py         # Sandbox security
│   └── utils/                  # Utilities
│       ├── __init__.py
│       ├── logging.py          # Logging configuration
│       ├── crypto.py           # Encryption/decryption
│       └── files.py            # File handling
├── scripts/                    # Installation scripts
│   ├── install.sh              # Main installation script
│   ├── update.sh               # Update script
│   └── download_platform_tools.sh # ADB download script
├── config/                     # Configuration files
│   ├── default_config.json     # Default configuration
│   └── default_config.example.json # Example configuration
├── logs/                       # Log directory
├── platform-tools/             # Android platform tools
└── temp/                       # Temporary file storage
    ├── workflows/              # Workflow temporary files
    ├── screenshots/            # Screenshot temporary files
    └── media/                  # Media temporary files
```

## Key Components

### device_manager
Handles all device connection management, command execution, and connection monitoring. The separation into multiple files keeps concerns separated while maintaining a unified interface.

### actions
Contains modules for executing different types of actions on devices. Each action type has its own module but follows a common interface defined in base.py.

### keyboard
Manages communication with the custom keyboard app, including sending typing sequences and handling keyboard responses.

### verification
Handles screen verification against references provided in workflow packages.

### cloud
Manages WebSocket communication with Cloud, including message handling, reconnection logic, and binary data transfer.

### workflows
Executes workflows received from Cloud, managing sequences, steps, and reporting results.

### sandbox
Provides a secure environment for executing injected code (special sequences and recovery scripts).

### utils
Contains utility functions used across the codebase, including logging, encryption, and file handling.

This structure keeps the code modular and maintainable while supporting all the functionality we've defined for Control.

Let's define a clear package structure for communications going into Control. This structure needs to be comprehensive enough to handle all types of operations while remaining as simple as possible.

# Control Component Package Structures

## Workflow Package Structure

The primary package type sent to Control will be workflow packages. These should contain:

```json
{
  "package_type": "workflow",
  "package_id": "unique_identifier",
  "workflow": {
    "workflow_id": "workflow_unique_id",
    "name": "Workflow Name",
    "client_id": "client_identifier",
    "priority": 1,
    "sequences": [
      {
        "sequence_id": "sequence_unique_id",
        "name": "Sequence Name",
        "expected_screens": [
          "screen_id_1",
          "screen_id_2"
        ],
        "steps": [
          {
            "step_id": "step_unique_id",
            "type": "tap",
            "coordinates": [540, 960],
            "expected_screen_after": "screen_id_2",
            "verification_timeout": 5
          },
          {
            "step_id": "step_unique_id_2",
            "type": "swipe",
            "start_coordinates": [540, 1200],
            "end_coordinates": [540, 600],
            "duration": 300,
            "expected_screen_after": "screen_id_1",
            "verification_timeout": 5
          },
          {
            "step_id": "step_unique_id_3",
            "type": "text",
            "keyboard_sequence": {
              "sequence": [
                {"action": "type", "text": "Hello", "delay_after": 0.2},
                {"action": "delay", "duration": 0.5},
                {"action": "type", "text": " world!", "delay_after": 0.2}
              ]
            },
            "expected_screen_after": "screen_id_2",
            "verification_timeout": 5
          }
        ]
      }
    ],
    "conditional_logic": [
      {
        "condition_id": "condition_1",
        "after_step_id": "step_unique_id", 
        "condition_type": "screen_match",
        "screen_id": "screen_id_2",
        "if_true": "continue",
        "if_false": "sequence_unique_id_2"
      }
    ]
  },
  "screen_registry": {
    "screen_id_1": {
      "name": "Home Screen",
      "image": "screen_id_1.png",
      "validation_regions": [
        {"x1": 100, "y1": 200, "x2": 300, "y2": 400},
        {"x1": 400, "y1": 500, "x2": 600, "y2": 700}
      ]
    },
    "screen_id_2": {
      "name": "Profile Screen", 
      "image": "screen_id_2.png",
      "validation_regions": [
        {"x1": 50, "y1": 150, "x2": 250, "y2": 350}
      ]
    }
  },
  "media_files": [
    "screen_id_1.png",
    "screen_id_2.png",
    "upload_video.mp4" 
  ],
  "device_id": "192.168.1.101:5555",
  "timestamp": "2025-03-25T14:30:00Z",
  "execution_options": {
    "retry_count": 3,
    "debug_mode": false
  }
}
```

## Live Command Package Structure

For direct commands in live mode:

```json
{
  "package_type": "live_command",
  "package_id": "unique_identifier",
  "command": {
    "command_id": "command_unique_id",
    "type": "tap",
    "coordinates": [540, 960],
    "verify_screen": false,
    "return_screenshot": true
  },
  "device_id": "192.168.1.101:5555",
  "session_id": "live_session_id",
  "timestamp": "2025-03-25T14:35:00Z"
}
```

## Special Sequence Package Structure

For injecting special sequences:

```json
{
  "package_type": "special_sequence",
  "package_id": "unique_identifier",
  "sequence": {
    "sequence_id": "sequence_unique_id",
    "name": "Special Sequence Name",
    "code": "... Python code for the special sequence ...",
    "parameters": {
      "param1": "value1",
      "param2": "value2"
    }
  },
  "device_id": "192.168.1.101:5555",
  "timestamp": "2025-03-25T14:40:00Z"
}
```

## Recovery Script Package Structure

For recovery scripts:

```json
{
  "package_type": "recovery_script", 
  "package_id": "unique_identifier",
  "script": {
    "script_id": "script_unique_id",
    "workflow_id": "original_workflow_id",
    "code": "... Python code with embedded API keys ...",
    "context": {
      "last_known_screen": "screen_id_1",
      "failed_step_id": "step_unique_id_2"
    }
  },
  "device_id": "192.168.1.101:5555",
  "timestamp": "2025-03-25T14:45:00Z"
}
```

## Binary Data Transfer

For screenshots and media files, we'll use WebSocket binary frames with a simple header structure to identify the content:

```
[4 bytes package_id][4 bytes content_id][4 bytes content_length][content_bytes]
```

This allows efficient transfer of binary data within the same WebSocket connection.

This package structure provides all the necessary information for Control to execute operations while maintaining simplicity and keeping most intelligence outside of Control itself.