# Active Context: Control System

## Current Focus

We are currently focused on consolidating the existing components into a unified Control system that can:

1. Receive and execute workflow packages from Core
2. Handle screen verification against provided references
3. Execute special sequences and recovery scripts
4. Maintain reliable device connections
5. Communicate with Cloud via WebSockets

This consolidation brings together functionality from several existing components:
- `connection_manager.py` for device connections
- `screen_verifier.py` for screen verification
- `explorer_7.py` for action recording
- `player_7.py` for action playback
- Various utility scripts for device control

## Recent Decisions

### Architecture Decisions

1. **Four-Component System**: 
   - Core: Central intelligence and database
   - Control: Device execution layer (this component)
   - Cloud: Communication relay
   - Connect: User interface

2. **Workflow Execution Flow**:
   - Core packages entire workflows with necessary screens
   - Control executes locally with temporary storage
   - Unknown screens sent to Core for identification
   - Recovery handled through injected FarmCLI scripts

3. **Media Handling**:
   - Simple redundant storage approach for screenshots
   - Binary file transfers for screenshots and media
   - Temporary storage in Control with cleanup after execution

4. **Scheduling Approach**:
   - Core-managed scheduling for all tasks
   - Core handles randomization within time windows
   - Core manages conflicts across all devices

### Implementation Decisions

1. **Repository Structure**:
   - Modular directory structure with separate components
   - Platform-tools downloaded during installation
   - Configuration via environment variables and config files

2. **Communication Protocol**:
   - WebSockets for real-time communication
   - JSON for command and status messages
   - Binary transfers for screenshots and media

3. **Recovery Approach**:
   - FarmCLI as injected special sequences
   - API keys included in injected scripts
   - Direct API calls from Control for performance

## Current Challenges

1. **Integration Complexity**: Bringing together multiple existing components with different designs
2. **WebSocket Implementation**: Ensuring reliable bidirectional communication with binary support
3. **Special Sequence Security**: Safely executing injected code while protecting API keys
4. **Device Connection Reliability**: Maintaining stable connections to multiple devices
5. **Performance Optimization**: Ensuring efficient execution across many devices

## Next Steps

### Immediate Tasks

1. Create the basic Control repository structure
2. Implement the WebSocket client for Cloud communication
3. Integrate the existing device connection manager
4. Implement the workflow executor component
5. Develop the special sequence handler

### Short-Term Goals

1. Complete a working prototype of Control that can execute basic workflows
2. Implement screen verification against workflow packages
3. Add support for special sequences and recovery scripts
4. Develop comprehensive logging and error handling
5. Create installation and update scripts

### Medium-Term Goals

1. Optimize performance for handling multiple devices
2. Implement robust error recovery and reconnection logic
3. Add support for all action types and verification methods
4. Develop comprehensive testing suite
5. Create monitoring and diagnostics tools

## Open Questions

1. How should Control handle network interruptions during workflow execution?
2. What's the optimal approach for managing device connection pools?
3. How can we optimize screen verification for better performance?
4. What metrics should Control collect and report to Core?
5. How should Control prioritize tasks when managing multiple devices?

## Recent Changes

- Consolidated architecture decisions from discussions
- Defined the workflow execution and recovery process
- Established the repository structure and deployment approach
- Clarified the role of Control within the larger system
- Determined the approach for handling media and screenshots
