
# Control - Device Automation Agent

Control is a automation agent for managing and executing operations on multiple Android devices. It serves as the execution layer that interacts directly with connected phones via ADB, executing workflows, verifying screens, and reporting results back to Cloud.

## System Architecture

Control is part of a larger automation platform with four main components:

1. **Control**: This component (contained in this repository), which executes operations on physical devices
2. **Cloud**: A relay service that handles communication between components
3. **Core**: The central intelligence and decision-making component
4. **Connect**: The user interface for monitoring and interacting with the system

Control communicates exclusively with Cloud, acting as a thin execution layer that receives packages, executes them on devices, and reports results back.

## Important Understanding

Control does NOT handle logic or planning. Only execution and reporting. For example the reference code includes tap.py and swipe.py and type.py that contain

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



