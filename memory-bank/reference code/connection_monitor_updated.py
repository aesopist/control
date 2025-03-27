import sys
import time
import logging
import datetime
from pathlib import Path
from typing import Dict, Optional
from connection_manager import ConnectionManager
from connection_discord_bot_singleton import ConnectionBot

class ConnectionMonitor:
    def __init__(self):
        try:
            print("Initializing ConnectionMonitor...")
            # Initialize paths
            self.base_path = Path(__file__).parent.resolve()
            self.logs_path = self.base_path / "logs"
            self.logs_path.mkdir(parents=True, exist_ok=True)
            
            # Get singleton instances
            self.connection_manager = ConnectionManager.get_instance()
            
            # Initialize Discord bot
            self.discord_bot = ConnectionBot.get_instance()
            
            self.setup_logging()
            self.last_status = {}
            self.last_heartbeat_time = 0
            print("ConnectionMonitor initialized successfully")
        except Exception as e:
            print(f"Failed to initialize ConnectionMonitor: {e}", file=sys.stderr)
            raise
        
    def setup_logging(self):
        log_file = self.logs_path / "connection_monitor.log"
        
        # Configure both file and console logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - ConnectionMonitor - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('ConnectionMonitor')
        
    def check_device_connections(self) -> Dict[str, Dict]:
        """Check current device connections and return status changes"""
        current_status = self.connection_manager.get_available_devices()
        changes = {}
        
        # Check for devices that were previously connected but are now disconnected
        for device_name in self.last_status:
            if device_name not in current_status:
                changes[device_name] = {
                    "status": "disconnected",
                    "previous": self.last_status[device_name]
                }
                
        # Check for new connections or connection type changes
        for device_name, info in current_status.items():
            if device_name not in self.last_status:
                changes[device_name] = {
                    "status": "connected",
                    "info": info
                }
            elif self.last_status[device_name] != info:
                changes[device_name] = {
                    "status": "changed",
                    "previous": self.last_status[device_name],
                    "current": info
                }
                
        self.last_status = current_status
        return changes

    def try_connect_wifi_devices(self):
        """Attempt to connect to known WiFi devices that aren't currently connected"""
        # Let ConnectionManager handle reconnection attempts
        # We just need to check for disconnections
        pass
        
    def try_connect_device(self, friendly_name: str, device_info: dict) -> bool:
        """Attempt to connect to a device and report failures
        
        Args:
            friendly_name: Name of the device (e.g. 'phone1')
            device_info: Device config info containing ip_address
            
        Returns:
            bool: True if connection successful, False if failed
        """
        if "ip_address" not in device_info:
            error_msg = f"{friendly_name}: No IP address configured"
            print(f"X {error_msg}")
            self.logger.error(error_msg)
            
            # Send notification directly to Discord
            self.discord_bot.send_notification(f"{friendly_name}: {error_msg}")
            return False
            
        ip_with_port = f"{device_info['ip_address']}:5555"
        print(f"Attempting to connect to {friendly_name} ({ip_with_port})...")
        
        try:
            result = self.connection_manager.device_service.connect_device(ip_with_port)
            if not result:
                error_msg = f"{friendly_name}: Failed to connect - device not responding"
                print(f"X {error_msg}")
                
                # Send notification directly to Discord
                self.discord_bot.send_notification(f"{friendly_name}: {error_msg}")
                return False
                
            print(f"+ Successfully connected to {friendly_name}")
            return True
            
        except Exception as e:
            error_msg = f"{friendly_name}: Connection error - {str(e)}"
            print(f"X {error_msg}")
            
            # Send notification directly to Discord
            self.discord_bot.send_notification(f"{friendly_name}: {error_msg}")
            return False
            
    def print_current_device_status(self):
        """Print the current status of all devices with timestamp"""
        # Format time as HH:MMam/pm
        current_time = datetime.datetime.now()
        hour = current_time.hour
        am_pm = "am" if hour < 12 else "pm"
        if hour > 12:
            hour -= 12
        if hour == 0:
            hour = 12
        formatted_time = f"{hour}:{current_time.minute:02d}{am_pm}"
        
        print(f"\nCurrent Device Status TIME ({formatted_time}):")
        current_devices = self.connection_manager.get_available_devices()
        
        # Show connected devices
        for name, info in current_devices.items():
            print(f"+ {name} ({info['connection_type']} - {info['device_id']})")
            
        # Show disconnected devices
        for device_id, info in self.connection_manager.device_config["devices"].items():
            friendly_name = info["friendly_name"]
            if friendly_name not in current_devices:
                print(f"X {friendly_name}: disconnected")
            
    def run(self, check_interval: int = 5):
        """Run the connection monitor with specified check interval"""
        print(f"\nStarting connection monitor with {check_interval} second interval...")
        self.logger.info("Starting connection monitor...")
        
        # Initial device check
        print("\nInitial device status:")
        current_devices = self.connection_manager.get_available_devices()
        
        # Show connected devices
        for name, info in current_devices.items():
            print(f"+ {name} ({info['connection_type']} - {info['device_id']})")
            
        # Try to connect any missing devices
        for device_id, info in self.connection_manager.device_config["devices"].items():
            friendly_name = info["friendly_name"]
            if friendly_name not in current_devices:
                print(f"X {friendly_name}: disconnected")
                if self.try_connect_device(friendly_name, info):
                    # If connection successful, add to current devices
                    current_devices[friendly_name] = {
                        "connection_type": "wifi",
                        "device_id": f"{info['ip_address']}:5555"
                    }
        
        print(f"\nMonitoring {len(current_devices)} connected devices...")
        print("Will notify about disconnections and connection failures\n")
        
        # Track last known status to detect disconnections
        last_known = current_devices
        
        while True:
            try:
                current_devices = self.connection_manager.get_available_devices()
                
                # Check for disconnections
                for name in last_known:
                    if name not in current_devices:
                        disconnect_msg = f"{name} disconnected"
                        print(f"! {disconnect_msg}")
                        
                        # Send notification directly to Discord
                        self.discord_bot.send_notification(f"{name}: disconnected")
                        
                        # Try to reconnect
                        device_info = None
                        for _, info in self.connection_manager.device_config["devices"].items():
                            if info["friendly_name"] == name:
                                device_info = info
                                break
                                
                        if device_info:
                            self.try_connect_device(name, device_info)
                
                # Update last known status
                last_known = current_devices
                
                # Print heartbeat status every 30 seconds
                current_time = time.time()
                if current_time - self.last_heartbeat_time >= 30:
                    self.print_current_device_status()
                    self.last_heartbeat_time = current_time
                
                time.sleep(check_interval)
                
            except Exception as e:
                error_msg = f"Error in connection monitor: {str(e)}"
                print(error_msg, file=sys.stderr)
                self.logger.error(error_msg)
                time.sleep(check_interval)

if __name__ == "__main__":
    monitor = ConnectionMonitor()
    time.sleep(3)  # Give ConnectionManager time to initialize
    monitor.run()
