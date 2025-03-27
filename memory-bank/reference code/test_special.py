#!/usr/bin/env python
"""
Test script for running scripts from the 'special' directory on selected devices.
Allows selection of a connected device and a script to run.
"""

import os
import sys
import time
import importlib.util
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from connection_manager import ConnectionManager

def get_available_devices() -> Dict[str, dict]:
    """
    Get all available devices through ConnectionManager.
    
    Returns:
        Dict mapping friendly names to device info.
    """
    connection_manager = ConnectionManager.get_instance()
    
    # Wait 3 seconds for ConnectionManager to initialize
    print("Initializing ConnectionManager...")
    time.sleep(3)
    
    # Get all available devices
    devices = connection_manager.get_available_devices()
    
    return devices

def get_special_scripts() -> List[Path]:
    """
    Get all Python scripts in the special directory.
    
    Returns:
        List of Path objects for Python scripts in the special directory.
    """
    special_dir = Path(__file__).parent.parent / "special"
    scripts = list(special_dir.glob("*.py"))
    
    # Filter out __init__.py and __pycache__ files
    scripts = [s for s in scripts if not s.name.startswith("__")]
    
    return sorted(scripts)

def select_from_options(options: List[Tuple[str, str]], prompt: str) -> Optional[str]:
    """
    Present a numbered list of options to the user and get their selection.
    
    Args:
        options: List of (value, display_text) tuples
        prompt: Text to show when asking for selection
    
    Returns:
        The selected value or None if selection failed
    """
    if not options:
        print("No options available.")
        return None
    
    print("\n" + prompt)
    print("=" * len(prompt))
    
    for i, (_, display_text) in enumerate(options, 1):
        print(f"{i}. {display_text}")
    
    try:
        choice = input("\nEnter number (or 'q' to quit): ")
        if choice.lower() == 'q':
            return None
        
        index = int(choice) - 1
        if 0 <= index < len(options):
            return options[index][0]
        else:
            print(f"Invalid choice. Please enter a number between 1 and {len(options)}.")
            return select_from_options(options, prompt)
    except ValueError:
        print("Please enter a number.")
        return select_from_options(options, prompt)

def run_script_with_device(script_path: Path, device_id: str) -> bool:
    """
    Run a script from the special directory with the specified device ID.
    
    Args:
        script_path: Path to the script to run
        device_id: Device ID to pass to the script
    
    Returns:
        True if successful, False otherwise
    """
    try:
        script_name = script_path.stem
        print(f"\nRunning '{script_name}' with device '{device_id}'...\n")
        
        # Run the script directly with the device ID as an argument
        # This assumes all special scripts are designed to take a device_id as their only argument
        result = subprocess.run(
            [sys.executable, str(script_path), device_id],
            check=False
        )
        
        if result.returncode == 0:
            print(f"\nScript '{script_name}' completed successfully.")
            return True
        else:
            print(f"\nScript '{script_name}' failed with exit code {result.returncode}.")
            return False
            
    except Exception as e:
        print(f"Error running script: {e}")
        return False

def main():
    """Main entry point."""
    try:
        print("\nSpecial Script Runner")
        print("====================")
        
        # Get available devices
        print("\nGetting available devices...")
        devices = get_available_devices()
        
        if not devices:
            print("\nNo devices found. Please connect a device and try again.")
            return
        
        # Format device options for selection
        device_options = []
        for friendly_name, info in devices.items():
            device_id = info.get('device_id', '')
            device_options.append((device_id, f"{friendly_name} ({device_id})"))
        
        # Let user select a device
        selected_device = select_from_options(device_options, "Select a device")
        if not selected_device:
            print("\nNo device selected. Exiting.")
            return
        
        # Get scripts from special directory
        scripts = get_special_scripts()
        
        if not scripts:
            print("\nNo scripts found in the 'special' directory.")
            return
        
        # Format script options for selection
        script_options = []
        for script in scripts:
            # Read the first docstring line if available
            description = ""
            try:
                spec = importlib.util.spec_from_file_location(script.stem, script)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if module.__doc__:
                    description = f" - {module.__doc__.strip().split('\n')[0]}"
            except:
                pass
            
            script_options.append((str(script), f"{script.stem}{description}"))
        
        # Let user select a script
        selected_script = select_from_options(script_options, "Select a script to run")
        if not selected_script:
            print("\nNo script selected. Exiting.")
            return
        
        # Run the selected script with the selected device
        run_script_with_device(Path(selected_script), selected_device)
        
    except KeyboardInterrupt:
        print("\nOperation interrupted. Exiting.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
