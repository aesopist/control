#!/usr/bin/env python
"""
Core Device Operations Module
Provides basic ADB command execution and fundamental device interactions.
"""

import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict

from error_manager import ErrorManager, ErrorSeverity, ErrorCategory

class CoreDeviceOps:
    """
    Core device operations for interacting with Android devices via ADB.
    
    This class provides the fundamental operations needed to interact with
    an Android device, serving as the foundation for higher-level utilities.
    """
    
    def __init__(self, device_id: str, connection_manager=None):
        """
        Initialize device operations with a device ID
        
        Args:
            device_id: ADB device identifier
            connection_manager: Optional connection manager instance
        """
        if connection_manager is None:
            from connection_manager import ConnectionManager
            connection_manager = ConnectionManager.get_instance()
            
        self.connection_manager = connection_manager
        self.device_id = device_id
        
        # Initialize paths
        self.base_path = Path(__file__).parent.parent
        self.adb_path = self.base_path / "platform-tools" / "adb.exe"
        
        # Initialize error manager
        self.error_manager = ErrorManager(self.base_path)
        
        # Setup logging
        self.log_path = self.base_path / "logs"
        self.log_path.mkdir(exist_ok=True)
        
        # Create a unique logger instance for this device
        self.logger = logging.getLogger(f'Device_{device_id}')
        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_path / f"device_{device_id}.log")
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)

    def execute_command(self, command: List[str], binary_output: bool = False) -> Tuple[bool, bytes | str]:
        """
        Execute an ADB command with error handling
        
        Args:
            command: List of command arguments to pass to ADB
            binary_output: If True, return bytes output instead of decoded string
            
        Returns:
            Tuple of (success, output) where output is bytes or string based on binary_output
        """
        try:
            full_command = [str(self.adb_path), "-s", self.device_id] + command
            self.logger.info(f"Executing: {' '.join(full_command)}")
            
            result = subprocess.run(
                full_command,
                capture_output=True
            )
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, full_command)
                
            return True, result.stdout if binary_output else result.stdout.decode()
            
        except subprocess.CalledProcessError as e:
            self.error_manager.handle_error(
                device_name=self.device_id,
                error=e,
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.DEVICE
            )
            return False, b"" if binary_output else str(e)

    def screenshot(self, reason: str = "", max_retries: int = 3, retry_delay: float = 1.0) -> Optional[bytes]:
        """
        Take screenshot and return raw bytes with retry mechanism
        
        Args:
            reason: Optional reason for taking screenshot (for logs)
            max_retries: Number of attempts to make before giving up
            retry_delay: Seconds to wait between retries
            
        Returns:
            Raw screenshot data as bytes or None on failure
        """
        for attempt in range(max_retries):
            success, output = self.execute_command(["exec-out", "screencap -p"], binary_output=True)
            if success and output and len(output) > 1000:  # Ensure we got meaningful data
                return output
            
            if attempt < max_retries - 1:
                self.logger.warning(f"Screenshot attempt {attempt+1} failed or returned invalid data. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                
        self.logger.error(f"Failed to take screenshot after {max_retries} attempts")
        return None

    def tap(self, x: int, y: int) -> bool:
        """
        Execute tap at coordinates
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Tapping at coordinates: ({x}, {y})")
        return self.execute_command(["shell", f"input touchscreen tap {x} {y}"])[0]

    def key_event(self, keycode: int) -> bool:
        """
        Send keycode to device
        
        Args:
            keycode: Android keycode to send
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Sending keycode: {keycode}")
        return self.execute_command(["shell", f"input keyevent {keycode}"])[0]

    def navigate_back(self) -> bool:
        """
        Press back button (convenience method)
        
        Returns:
            True if successful, False otherwise
        """
        return self.key_event(4)  # KEYCODE_BACK = 4
        
    def sleep_device(self) -> bool:
        """
        Put device to sleep (turn off screen)
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Putting device {self.device_id} to sleep")
        return self.key_event(26)  # KEYCODE_POWER = 26
        
    def wake_device(self) -> bool:
        """
        Wake device (turn on screen)
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Waking device {self.device_id}")
        # Send WAKEUP keyevent
        success = self.key_event(224)  # KEYCODE_WAKEUP = 224
        
        if success:
            # Also send MENU key to ensure it's fully awake
            self.key_event(82)  # KEYCODE_MENU = 82
            
        return success
