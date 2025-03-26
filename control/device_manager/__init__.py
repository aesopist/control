"""
Device management package for Control component.
Handles device connections, command execution, and status monitoring.
"""

from .connection import DeviceConnection
from .command import DeviceCommand
from .monitor import ConnectionMonitor

__all__ = [
    'DeviceConnection',
    'DeviceCommand',
    'ConnectionMonitor',
    'DeviceManager'
]

class DeviceError(Exception):
    """Device operation errors."""
    pass

class DeviceManager:
    """
    Manages device connections and operations.
    Implements the Singleton pattern to ensure consistent device management.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeviceManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Initialize components
        self.connection = DeviceConnection()
        self.command = DeviceCommand()
        self.monitor = ConnectionMonitor()
        
        self._initialized = True
    
    def get_available_devices(self):
        """Get all available connected devices."""
        return self.connection.get_available_devices()
    
    def execute_command(self, device_id, command, binary_output=False, timeout=30):
        """
        Execute ADB command on device
        
        Args:
            device_id: Device identifier
            command: Command to execute
            binary_output: Whether to return binary output
            timeout: Timeout in seconds
            
        Returns:
            (success, output) tuple
        """
        return self.command.execute(device_id, command, binary_output, timeout)
    
    def capture_screenshot(self, device_id):
        """
        Capture screenshot from device
        
        Args:
            device_id: Device identifier
            
        Returns:
            Screenshot data as bytes
        """
        return self.command.capture_screenshot(device_id)
    
    def start_monitoring(self):
        """Start monitoring device connections."""
        return self.monitor.start()
    
    def stop_monitoring(self):
        """Stop monitoring device connections."""
        return self.monitor.stop()
    
    def connect_device(self, device_id):
        """
        Connect to a device
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if successful, False otherwise
        """
        return self.connection.connect(device_id)
    
    def disconnect_device(self, device_id):
        """
        Disconnect from a device
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if successful, False otherwise
        """
        return self.connection.disconnect(device_id)
