"""
Device command execution for Control component.
Handles executing commands on devices and processing results.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import threading

from ..config import Config

class DeviceCommand:
    """
    Executes commands on devices via ADB.
    """
    
    def __init__(self):
        # Get configuration
        self.config = Config()
        
        # Initialize paths
        self.base_path = Path(__file__).parent.parent.parent
        self.adb_path = self.base_path / "platform-tools" / "adb.exe"
        
        # Initialize logging
        self.logger = logging.getLogger("DeviceCommand")
        
        # Command locks for concurrent access
        self._command_locks = {}  # device_id -> lock
    
    def execute(self, device_id: str, command: List[str], binary_output: bool = False, 
                timeout: int = 30) -> Tuple[bool, Union[str, bytes]]:
        """
        Execute an ADB command on a device
        
        Args:
            device_id: Device identifier
            command: ADB command arguments
            binary_output: Whether to return binary output
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (success, output) where output is string or bytes
        """
        # Get or create lock for this device
        if device_id not in self._command_locks:
            self._command_locks[device_id] = threading.Lock()
        
        # Execute with lock to prevent concurrent commands to same device
        with self._command_locks[device_id]:
            try:
                # Build full command
                full_command = [str(self.adb_path), "-s", device_id] + command
                self.logger.debug(f"Executing: {' '.join(full_command)}")
                
                # Execute command
                result = subprocess.run(
                    full_command,
                    capture_output=True,
                    timeout=timeout
                )
                
                # Check result
                if result.returncode != 0:
                    self.logger.error(f"Command failed for {device_id}: {result.stderr}")
                    return False, result.stderr.decode() if not binary_output else b''
                
                # Return output
                return True, result.stdout if binary_output else result.stdout.decode()
                
            except subprocess.TimeoutExpired:
                self.logger.error(f"Command timed out for {device_id}")
                return False, f"Command timed out after {timeout} seconds" if not binary_output else b''
                
            except Exception as e:
                self.logger.error(f"Error executing command for {device_id}: {e}")
                return False, str(e) if not binary_output else b''
    
    def capture_screenshot(self, device_id: str, max_retries: int = 3) -> Optional[bytes]:
        """
        Capture screenshot from device
        
        Args:
            device_id: Device identifier
            max_retries: Maximum number of retry attempts
            
        Returns:
            Screenshot data as bytes or None on failure
        """
        for attempt in range(max_retries):
            success, output = self.execute(
                device_id, 
                ["exec-out", "screencap", "-p"], 
                binary_output=True
            )
            
            if success and output and len(output) > 1000:  # Ensure we got meaningful data
                return output
            
            if attempt < max_retries - 1:
                self.logger.warning(f"Screenshot attempt {attempt+1} failed. Retrying...")
                time.sleep(1)
        
        self.logger.error(f"Failed to capture screenshot after {max_retries} attempts")
        return None
    
    def tap(self, device_id: str, x: int, y: int) -> bool:
        """
        Perform tap operation on device (direct method, not humanized)
        
        Args:
            device_id: Device identifier
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful, False otherwise
        """
        success, _ = self.execute(device_id, ["shell", f"input tap {x} {y}"])
        return success
    
    def swipe(self, device_id: str, start_x: int, start_y: int, 
              end_x: int, end_y: int, duration_ms: int = 300) -> bool:
        """
        Perform swipe operation on device (direct method, not humanized)
        
        Args:
            device_id: Device identifier
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration_ms: Swipe duration in milliseconds
            
        Returns:
            True if successful, False otherwise
        """
        success, _ = self.execute(
            device_id, 
            ["shell", f"input swipe {start_x} {start_y} {end_x} {end_y} {duration_ms}"]
        )
        return success
    
    def key_event(self, device_id: str, keycode: int) -> bool:
        """
        Send key event to device
        
        Args:
            device_id: Device identifier
            keycode: Android keycode to send
            
        Returns:
            True if successful, False otherwise
        """
        success, _ = self.execute(device_id, ["shell", f"input keyevent {keycode}"])
        return success
    
    def wake_device(self, device_id: str) -> bool:
        """
        Wake device screen
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if successful, False otherwise
        """
        # Send KEYCODE_WAKEUP (224)
        success = self.key_event(device_id, 224)
        
        if success:
            # Also send MENU key to ensure it's fully awake
            self.key_event(device_id, 82)
            
        return success
    
    def sleep_device(self, device_id: str) -> bool:
        """
        Put device to sleep
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if successful, False otherwise
        """
        # Send KEYCODE_POWER (26)
        return self.key_event(device_id, 26)
