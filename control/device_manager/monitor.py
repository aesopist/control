"""
Device connection monitoring for Control component.
Handles monitoring device connections and reconnection attempts.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Set

from ..config import Config
from .connection import DeviceConnection

class ConnectionMonitor:
    """
    Monitors device connections and handles reconnection attempts.
    """
    
    def __init__(self):
        # Get configuration
        self.config = Config()
        
        # Initialize logging
        self.logger = logging.getLogger("ConnectionMonitor")
        
        # Reference to connection manager
        self.connection = DeviceConnection()
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread = None
        self._stop_event = threading.Event()
        
        # Connection tracking
        self._last_known_devices = set()
    
    def start(self):
        """Start connection monitoring"""
        if self._monitoring:
            return False
        
        # Clear stop event
        self._stop_event.clear()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()
        
        self._monitoring = True
        self.logger.info("Connection monitoring started")
        return True
    
    def stop(self):
        """Stop connection monitoring"""
        if not self._monitoring:
            return False
        
        # Set stop event
        self._stop_event.set()
        
        # Wait for thread to finish
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            
        self._monitoring = False
        self.logger.info("Connection monitoring stopped")
        return True
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        check_interval = self.config.get('device_check_interval', 5)
        
        while not self._stop_event.is_set():
            try:
                # Get current connected devices
                current_devices = self.connection.get_available_devices()
                current_device_ids = set(current_devices.keys())
                
                # Check for disconnections
                for device_id in self._last_known_devices:
                    if device_id not in current_device_ids:
                        # Device disconnected
                        self.logger.warning(f"Device {device_id} disconnected")
                        self._handle_disconnection(device_id)
                
                # Update last known devices
                self._last_known_devices = current_device_ids
                
                # Wait for next check
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in connection monitor: {e}")
                time.sleep(check_interval)
    
    def _handle_disconnection(self, device_id: str):
        """
        Handle device disconnection
        
        Args:
            device_id: Device identifier
        """
        # Only attempt reconnection for WiFi devices
        if ":" in device_id:
            self.logger.info(f"Attempting to reconnect to {device_id}")
            success = self.connection.connect(device_id)
            
            if success:
                self.logger.info(f"Successfully reconnected to {device_id}")
            else:
                self.logger.warning(f"Failed to reconnect to {device_id}")
