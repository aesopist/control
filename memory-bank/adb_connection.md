# ADB Wireless Connection for Control

The Control system assumes that all wireless ADB connections use port 5555. This is critical because:
- All connected devices are pre-configured to use port 5555.
- External ADB servers and APIs expect devices to communicate on port 5555.
- Control’s device management module (in `control/device_manager/connection.py`) uses the configuration parameter `adb_port`, defaulting to 5555 if not specified.

If you experience connectivity issues, please:
1. Verify that your devices are accessible on port 5555 (e.g., using `adb connect <device_ip>:5555`).
2. Run `adb devices` to confirm connectivity.
3. Shut down or reconfigure any conflicting ADB servers running on a different port.

### Screenshot Capture Method

For reliably capturing screenshots from devices over wireless ADB, use the following command:

    adb -s [device_ip]:5555 exec-out screencap -p > [output_file].png

This method leverages the "exec-out" option instead of "shell" to avoid extra carriage return characters or any extraneous output that might corrupt the PNG file. This has been validated on our devices and is the recommended procedure for all screenshot operations.
