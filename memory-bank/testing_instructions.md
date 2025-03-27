# Control Testing Instructions

This guide will help you test the Control component using the Compute Simulator.

## Requirements

Before starting, make sure you have:

1. Python 3.9+ installed
2. Control component code set up
3. ADB (Android Debug Bridge) installed and in your PATH
4. At least one Android device connected (or emulator running)

## Setup

1. Install required Python packages for the simulator:

```
pip install websockets pillow
```

## Running the Tests

### Step 1: Start the Compute Simulator

1. Open a terminal/command prompt
2. Navigate to the directory containing `compute_simulator.py`
3. Run the simulator:

```
python compute_simulator.py
```

The simulator will start a WebSocket server on localhost port 8765.

### Step 2: Start Control with Test Configuration

1. Open another terminal/command prompt
2. Navigate to your Control component directory
3. Run Control with the test configuration:

```
python -m control --config C:\Users\will\OneDrive\Desktop\test_config.json --debug
```

Control should start and connect to the Compute Simulator.

### Step 3: Use the Simulator to Send Workflows

In the Compute Simulator terminal, you should see:
```
Server running at ws://127.0.0.1:8765
```

You should also see a message when Control connects:
```
New client connected: control_test
```

Now you can use the interactive console to:

1. Enter `1` to send a test workflow
2. Enter the device ID when prompted (use the ID of a connected device, e.g., `192.168.1.201:5555`)

### Step 4: Observe Control's Behavior

In the Control terminal, you should see:
1. Receipt of the workflow package
2. Execution of the workflow steps
3. Screenshots being captured and compared
4. Results being sent back to the simulator

### Step 5: Test Live Commands

In the Compute Simulator:
1. Enter `2` to send a live command
2. Choose the command type (tap, swipe, or text)
3. Enter the required parameters
4. Observe the execution in Control's terminal

### Step 6: Test Special Sequences

In the Compute Simulator:
1. Enter `3` to send a special sequence
2. Enter the device ID
3. Observe the execution in Control's terminal

## Troubleshooting

### Control doesn't connect to the simulator
- Verify that the WebSocket URL in `test_config.json` matches the simulator address
- Check for any firewall or network issues
- Ensure Control is using the test configuration file

### Device commands not executing
- Verify that ADB is working by running `adb devices` in a terminal
- Check that the device ID is correct
- Make sure the device is properly connected and recognized by ADB

### Error in screen verification
- Check that PIL (Pillow) and OpenCV are properly installed
- Ensure the test image is being received by Control
- Verify that the validation regions are within the screen dimensions

## Expected Behavior

When everything is working correctly:

1. Control will connect to the simulator
2. Workflows and commands will be executed on the specified device
3. Screenshots will be taken and verified
4. Results will be sent back to the simulator
5. The simulator will display execution status

This testing setup allows you to validate Control's core functionality without needing to deploy the full system with Core and Cloud components.
