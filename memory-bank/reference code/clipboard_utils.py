#!/usr/bin/env python3
"""
Utility functions for clipboard operations using the SociaLlama Keyboard.
This module provides a clean interface for getting and setting clipboard content
by handling the special sequences that open the keyboard app.
"""

import os
import sys
import subprocess
from pathlib import Path

# Ensure base path is in sys.path for imports
base_path = Path(__file__).parent.parent
if str(base_path) not in sys.path:
    sys.path.append(str(base_path))

from utils.app_utils import get_current_app
from utils.device_id_converter import get_adb_device_id

def get_clipboard(device_id):
    """
    Get clipboard content from a device.
    
    Args:
        device_id: Device ID in any format (phoneX, IP:PORT, serial)
        
    Returns:
        Clipboard content as string
    """
    # Convert to ADB device ID format
    adb_device_id = get_adb_device_id(device_id)
    
    # Get the current app to return to
    current_app = get_current_app(adb_device_id)
    
    # Path to the special sequence script
    script_path = os.path.join(base_path, "special", "get_clipboard.py")
    
    # Run the special sequence
    try:
        result = subprocess.run(
            [sys.executable, script_path, adb_device_id, current_app],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting clipboard: {e}", file=sys.stderr)
        print(f"Error output: {e.stderr}", file=sys.stderr)
        return ""

def set_clipboard(device_id, content):
    """
    Set clipboard content on a device.
    
    Args:
        device_id: Device ID in any format (phoneX, IP:PORT, serial)
        content: Text content to set in clipboard
        
    Returns:
        True if successful, False otherwise
    """
    # Convert to ADB device ID format
    adb_device_id = get_adb_device_id(device_id)
    
    # Get the current app to return to
    current_app = get_current_app(adb_device_id)
    
    # Path to the special sequence script
    script_path = os.path.join(base_path, "special", "set_clipboard.py")
    
    # Run the special sequence
    try:
        result = subprocess.run(
            [sys.executable, script_path, adb_device_id, current_app, content],
            capture_output=True,
            text=True,
            check=True
        )
        return "successfully" in result.stdout.lower()
    except subprocess.CalledProcessError as e:
        print(f"Error setting clipboard: {e}", file=sys.stderr)
        print(f"Error output: {e.stderr}", file=sys.stderr)
        return False

# Example usage
if __name__ == "__main__":
    # This is just for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Test clipboard utilities")
    parser.add_argument("--device", default="phone1", help="Device ID")
    parser.add_argument("--get", action="store_true", help="Get clipboard content")
    parser.add_argument("--set", help="Set clipboard content")
    
    args = parser.parse_args()
    
    if args.get:
        content = get_clipboard(args.device)
        print(f"Clipboard content: {content}")
    
    if args.set:
        success = set_clipboard(args.device, args.set)
        if success:
            print(f"Successfully set clipboard content to: {args.set}")
        else:
            print("Failed to set clipboard content")
