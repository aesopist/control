# Technical Context: Control System

## Technologies Used

### Core Technologies

- **Python 3.9+**: Primary programming language for Control
- **ADB (Android Debug Bridge)**: Core tool for interacting with Android devices
- **WebSockets**: For real-time communication with Cloud
- **OpenCV/PIL**: For image processing and screen verification
- **SQLite**: For local caching and temporary storage

### External Services

- **OpenAI API**: Used for FarmCLI recovery scripts (ChatGPT)
- **Google AI API**: Used for element identification (Gemini)

### Development Tools

- **Git**: Version control
- **GitHub**: Repository hosting
- **VSCode**: Recommended IDE
- **pytest**: Testing framework

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Android platform-tools (ADB)
- Connected Android device(s) or emulator(s)
- Network access to Cloud relay

### Local Development Environment

1. Clone the Control repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables in `.env` file
4. Run in development mode: `python -m control --dev`

### Testing Environment

- Unit tests: `pytest tests/unit/`
- Integration tests: `pytest tests/integration/`
- End-to-end tests: `pytest tests/e2e/`

## Technical Constraints

### Device Limitations

- **Connection Stability**: ADB connections can be unstable and require monitoring
- **Device Performance**: Older devices may have slower response times
- **Screen Variations**: Different devices have different screen sizes and resolutions
- **OS Variations**: Different Android versions may have UI differences

### Network Considerations

- **Bandwidth**: Screenshot transfers require sufficient bandwidth
- **Latency**: High latency can affect real-time operations
- **Reliability**: Connection to Cloud must be maintained or recovered
- **Firewall Issues**: Corporate environments may block required ports

### Security Constraints

- **API Keys**: Must be securely managed for AI services
- **Device Access**: Physical security for devices is essential
- **Code Injection**: Special sequences must be executed in a controlled environment
- **Client Data**: Client account information must be protected

### Scaling Considerations

- **Memory Usage**: Each device requires memory for screenshots and workflow data
- **CPU Usage**: Screen verification is CPU-intensive
- **Concurrency**: Multiple devices must be managed simultaneously
- **Resource Limits**: Each Control instance should handle up to 60 devices

## Component Interactions

### Control ↔ Cloud

- WebSocket connection for real-time communication
- JSON messages for commands and status
- Binary transfers for screenshots and media
- Reconnection logic for reliability

### Control ↔ Devices

- ADB connection for device control
- Screenshot capture for verification
- Command execution for actions
- Custom keyboard app for text input

### Control ↔ Local Storage

- Temporary storage for workflow packages
- Screenshot caching for verification
- Session recording for action history
- Log files for debugging and auditing

## Performance Expectations

- **Action Execution**: < 500ms per action
- **Screen Verification**: < 100ms per verification
- **Recovery Initiation**: < 2s from unknown screen detection
- **Screenshot Capture**: < 300ms per screenshot
- **Concurrent Devices**: Support for up to 60 devices per instance
- **Memory Usage**: < 100MB base + ~10MB per active device

## Deployment Strategy

### Installation

- Automated installation script
- Platform-tools downloaded during installation
- Configuration via environment variables or config file
- Service installation for automatic startup

### Updates

- Git-based updates for code changes
- Version checking on startup
- Automatic update option
- Rollback capability for failed updates

### Monitoring

- Heartbeat signals to Cloud
- Status reporting for all devices
- Error logging with severity levels
- Performance metrics collection

By understanding these technical constraints and considerations, developers can build a robust Control component that integrates effectively with the larger system while maintaining performance and reliability.
