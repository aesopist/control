"""
Device connection management for Control component.
Handles connecting to devices, tracking connection status, and managing device information.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import json

from ..config import Config

class DeviceConnection:
    """
    Manages connections to physical devices via ADB.
    """
    
    def __init__(self):
        # Get configuration
        self.config = Config()
        
        # Initialize paths
        self.base_path = Path(__file__).parent.parent.parent
        self.adb_path = self.base_path / "platform-tools" / "adb.exe"
        
        # Initialize logging
        self.logger = logging.getLogger("DeviceConnection")
        
        # Device tracking
        self._devices = {}  # device_id -> device info
        self._device_locks = {}  # device_id -> lock
        
        # Load device configuration if available
        self._load_devices()
        
        # Start ADB server
        self._start_adb_server()
    
    def _start_adb_server(self):
        """Start ADB server if not running"""
        if hasattr(self, "_adb_server_started") and self._adb_server_started:
            return
        try:
            # Use shell=True to avoid the WinError 2 issue
            subprocess.run(f'"{self.adb_path}" start-server', shell=True, check=True, capture_output=True)
            self.logger.info("ADB server started")
            self._adb_server_started = True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start ADB server: {e}")
            raise Exception(f"Failed to start ADB server: {e}")
    
    def _load_devices(self):
        """Load devices from configuration"""
        devices_config = self.config.get('devices', {})
        
        for device_id, device_info in devices_config.items():
            self._devices[device_id] = {
                **device_info,
                'connected': False,
                'last_seen': None,
                'error_count': 0
            }
            self._device_locks[device_id] = threading.Lock()
    
    def get_available_devices(self) -> Dict[str, Dict]:
        """
        Get all available connected devices
        
        Returns:
            Dictionary of device_id -> device info
        """
        available = {}
        
        # Get connected devices via ADB
        try:
            result = subprocess.run(
                [str(self.adb_path), 'devices'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Parse output
            lines = result.stdout.splitlines()[1:]  # Skip "List of devices attached"
            for line in lines:
                if "\tdevice" in line:
                    device_id = line.split()[0]
                    
                    # Check if in our config, otherwise add basic info
                    if device_id in self._devices:
                        device_info = self._devices[device_id]
                        device_info['connected'] = True
                        available[device_id] = device_info
                    else:
                        # New device, not in config
                        available[device_id] = {
                            'device_id': device_id,
                            'friendly_name': f"unknown_{device_id}",
                            'connected': True
                        }
            
            # Check for devices connected via WiFi
            for device_id, info in self._devices.items():
                if 'ip_address' in info and device_id not in available:
                    ip_address = info['ip_address']
                    adb_port = info.get('adb_port', 5555)
                    
                    # Check if device responds
                    try:
                        ip_device_id = f"{ip_address}:{adb_port}"
                        check_result = subprocess.run(
                            [str(self.adb_path), '-s', ip_device_id, 'shell', 'echo', 'test'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        
                        if check_result.returncode == 0 and 'test' in check_result.stdout:
                            info['connected'] = True
                            available[ip_device_id] = info
                    except:
                        pass
        
        except Exception as e:
            self.logger.error(f"Error getting available devices: {e}")
        
        return available
    
    def connect(self, device_id: str) -> bool:
        """
        Connect to a device
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already connected
            if ":" in device_id:  # WiFi device
                # Just try to connect
                result = subprocess.run(
                    [str(self.adb_path), 'connect', device_id],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                success = 'connected' in result.stdout.lower()
                
                if success:
                    # Update status in tracking
                    device_info = self._devices.get(device_id)
                    if device_info:
                        device_info['connected'] = True
                        device_info['last_seen'] = time.time()
                    
                    self.logger.info(f"Connected to device {device_id}")
                else:
                    self.logger.error(f"Failed to connect to device {device_id}: {result.stderr}")
                
                return success
            else:
                # USB device - should already be connected
                # Just check if it's available
                return self._check_device_connection(device_id)
        
        except Exception as e:
            self.logger.error(f"Error connecting to device {device_id}: {e}")
            return False
    
    def disconnect(self, device_id: str) -> bool:
        """
        Disconnect from a device
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if ":" in device_id:  # WiFi device
                result = subprocess.run(
                    [str(self.adb_path), 'disconnect', device_id],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # Update status in tracking
                device_info = self._devices.get(device_id)
                if device_info:
                    device_info['connected'] = False
                
                return True  # ADB disconnect always "succeeds"
            else:
                # Can't disconnect USB devices
                return False
        
        except Exception as e:
            self.logger.error(f"Error disconnecting from device {device_id}: {e}")
            return False
    
    def _check_device_connection(self, device_id: str) -> bool:
        """Check if device is connected via ADB"""
        try:
            result = subprocess.run(
                [str(self.adb_path), '-s', device_id, 'shell', 'echo', 'test'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            success = result.returncode == 0 and 'test' in result.stdout
            
            # Update status in tracking
            device_info = self._devices.get(device_id)
            if device_info and success:
                device_info['connected'] = True
                device_info['last_seen'] = time.time()
            elif device_info:
                device_info['connected'] = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error checking device {device_id}: {e}")
            return False
