import logging
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import subprocess
import time

class AccountError(Exception):
    """Base exception for account management errors"""
    pass

class ConfigError(AccountError):
    """Configuration related errors"""
    pass

class ConnectionManager:
    """Manages device connections and configurations. 
    This is a singleton to ensure only one instance manages device connections."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'ConnectionManager':
        """Get the singleton instance of ConnectionManager"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def __init__(self):
        """Initialize the ConnectionManager. Use get_instance() instead of calling directly."""
        if ConnectionManager._instance is not None:
            raise RuntimeError("ConnectionManager is a singleton. Use get_instance() instead.")
            
        ConnectionManager._instance = self
        
        # Initialize paths
        self.base_path = Path(__file__).parent.resolve()
        self.config_path = self.base_path / "config"
        self.log_path = self.base_path / "logs"
        self.adb_path = self.base_path / "platform-tools" / "adb.exe"
        
        # Create required directories
        self._setup_directories()
        
        # Initialize logging
        self._setup_logging()
        
        # Load configurations
        self.device_config_file = self.config_path / "device_config.json"
        self.client_config_file = self.config_path / "client_config.json"
        self.assignments_file = self.config_path / "account_assignments.json"
        
        self.device_config = self._load_device_config()
        self.client_config = self._load_client_config()
        self.account_assignments = self._load_assignments()
        
        # Initialize device service and client
        from services.device_service.service import DeviceService
        from services.device_service.client import DeviceServiceClient
        import time
        
        # First ensure ADB server is running
        try:
            subprocess.run([str(self.adb_path), "start-server"], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start ADB server: {e}")
            raise AccountError("Failed to start ADB server") from e
            
        # Get or start device service singleton
        try:
            self.device_service = DeviceService.get_instance()
            if not self.device_service.start():
                raise AccountError("Failed to start device service")
            
            # Give service time to initialize if just started
            if not self.device_service.running:
                time.sleep(2)
            
            # Connect client
            self.device_client = DeviceServiceClient()
            self.device_client.connect()
            
            self.logger.info("ConnectionManager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize device service: {e}")
            raise AccountError("Failed to initialize device service") from e

    def _setup_directories(self) -> None:
        """Create and verify required directories"""
        try:
            self.config_path.mkdir(parents=True, exist_ok=True)
            self.log_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ConfigError(f"Failed to create required directories: {str(e)}")

    def _setup_logging(self) -> None:
        """Configure account-specific logging"""
        log_file = self.log_path / "connection_manager.log"
        
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - ConnectionManager - %(message)s'
        )
        
        self.logger = logging.getLogger('ConnectionManager')
        self.logger.setLevel(logging.INFO)

    def _atomic_save(self, data: dict, file_path: Path) -> None:
        """Save configuration with atomic write"""
        temp_file = file_path.with_suffix('.tmp')
        try:
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=4)
            temp_file.replace(file_path)
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise ConfigError(f"Failed to save configuration: {str(e)}")

    def _load_device_config(self) -> Dict:
        """Load device configuration"""
        try:
            if self.device_config_file.exists():
                with open(self.device_config_file) as f:
                    return json.load(f)
        except Exception as e:
            raise ConfigError(f"Failed to load device config: {str(e)}")
        return {}

    def _load_client_config(self) -> Dict:
        """Load client configuration"""
        try:
            if self.client_config_file.exists():
                with open(self.client_config_file) as f:
                    return json.load(f)
        except Exception as e:
            raise ConfigError(f"Failed to load client config: {str(e)}")
        return {}

    def _load_assignments(self) -> Dict:
        """Load account assignments"""
        try:
            if self.assignments_file.exists():
                with open(self.assignments_file) as f:
                    return json.load(f)
        except Exception as e:
            raise ConfigError(f"Failed to load assignments: {str(e)}")
        return {"version": "1.0.0", "assignments": {}, "account_health": {}}

    def get_device_friendly_name(self, device_id: str) -> str:
        """Get friendly name for device"""
        device_info = self.device_config["devices"].get(device_id)
        if not device_info:
            raise ConfigError(f"Unknown device ID: {device_id}")
        return device_info["friendly_name"]

    def get_device_id(self, identifier: str) -> str:
        """Get device ID from friendly name or ID"""
        # If it's already a device ID, verify it exists
        if identifier in self.device_config["devices"]:
            return identifier
            
        # Look up by friendly name
        for device_id, info in self.device_config["devices"].items():
            if info["friendly_name"] == identifier:
                return device_id
                
        raise ConfigError(f"Unknown device: {identifier}")

    def get_client_profile(self, device_name: str) -> Dict:
        """Get client profile for device"""
        for client_info in self.client_config["clients"].values():
            if device_name in client_info["account_profiles"]:
                return client_info["account_profiles"][device_name]
        raise ConfigError(f"No profile found for device: {device_name}")

    def get_active_account(self, device_name: str) -> Optional[str]:
        """Get active account for device"""
        device_id = self.get_device_id(device_name)
        device_info = self.device_config["devices"][device_id]
        return device_info.get("active_account")

    def set_active_account(self, device_name: str, account_name: str) -> None:
        """Set active account for device"""
        device_id = self.get_device_id(device_name)
        self.device_config["devices"][device_id]["active_account"] = account_name
        self._atomic_save(self.device_config, self.device_config_file)

    def add_account(self, device_name: str, account_name: str, email: str) -> None:
        """Add new account to assignments"""
        device_id = self.get_device_id(device_name)
        client_name = "FanVue"  # Hardcoded for Phase 1
        
        # Add to assignments
        self.account_assignments["assignments"][account_name] = {
            "client": client_name,
            "device": device_name,
            "status": "active",
            "login_type": "email",
            "login_info": {
                "login": email,
                "password": self.get_client_profile(device_name)["profile_password"]
            }
        }
        
        # Initialize health tracking
        self.account_assignments["account_health"]["forced_logins"][account_name] = 0
        self.account_assignments["account_health"]["captchas"][account_name] = 0
        self.account_assignments["account_health"]["last_active"][account_name] = datetime.now().isoformat()
        
        # Save changes
        self._atomic_save(self.account_assignments, self.assignments_file)

    def update_health_metrics(self, device_name: str, account_name: str, metric_type: str, value: any) -> None:
        """Update health metrics for both device and account"""
        timestamp = datetime.now().isoformat()
        device_id = self.get_device_id(device_name)
        
        # Update device metrics
        device_metrics = self.device_config["device_health"]
        if metric_type not in device_metrics:
            device_metrics[metric_type] = {}
        device_metrics[metric_type][device_id] = value
        device_metrics["last_checked"][device_id] = timestamp
        
        # Update account metrics
        account_metrics = self.account_assignments["account_health"]
        if metric_type not in account_metrics:
            account_metrics[metric_type] = {}
        account_metrics[metric_type][account_name] = value
        account_metrics["last_active"][account_name] = timestamp
        
        # Save both configs
        self._atomic_save(self.device_config, self.device_config_file)
        self._atomic_save(self.account_assignments, self.assignments_file)

    def increment_health_counter(self, device_name: str, account_name: str, counter_type: str) -> None:
        """Increment health counter for both device and account"""
        device_id = self.get_device_id(device_name)
        
        # Update device counter
        device_metrics = self.device_config["device_health"]
        if counter_type not in device_metrics:
            device_metrics[counter_type] = {}
        if device_id not in device_metrics[counter_type]:
            device_metrics[counter_type][device_id] = 0
        device_metrics[counter_type][device_id] += 1
        
        # Update account counter
        account_metrics = self.account_assignments["account_health"]
        if counter_type not in account_metrics:
            account_metrics[counter_type] = {}
        if account_name not in account_metrics[counter_type]:
            account_metrics[counter_type][account_name] = 0
        account_metrics[counter_type][account_name] += 1
        
        # Update last checked/active timestamps
        timestamp = datetime.now().isoformat()
        device_metrics["last_checked"][device_id] = timestamp
        account_metrics["last_active"][account_name] = timestamp
        
        # Save both configs
        self._atomic_save(self.device_config, self.device_config_file)
        self._atomic_save(self.account_assignments, self.assignments_file)

    def get_available_devices(self) -> Dict[str, Dict]:
        """Get all available devices with connection info
        
        Returns a dict mapping friendly names to device info:
        {
            "friendly_name": {
                "device_id": str,      # ADB device ID
                "connection_type": str, # "wifi" or "usb"
                "active_account": str,  # Currently active account name
            }
        }
        """
        available = {}
        
        # Get WiFi devices from Device Service
        service_devices = self.device_service.get_devices()
        
        # Get USB devices directly from ADB
        try:
            result = subprocess.run(
                [str(self.adb_path), "devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            usb_devices = set()
            for line in result.stdout.splitlines()[1:]:
                if "\tdevice" in line:
                    device_id = line.split()[0]
                    if ":" not in device_id:  # Not a WiFi device
                        usb_devices.add(device_id)
        except Exception as e:
            self.logger.error(f"Error checking USB devices: {str(e)}")
            usb_devices = set()
        
        # Combine device info with config
        for device_id, info in self.device_config["devices"].items():
            friendly_name = info["friendly_name"]
            ip_address = info.get("ip_address")
            ip_with_port = f"{ip_address}:5555" if ip_address else None
            
            # Check if device is connected via WiFi through Device Service
            if ip_with_port and ip_with_port in service_devices:
                available[friendly_name] = {
                    "device_id": ip_with_port,
                    "connection_type": "wifi",
                    "active_account": info.get("active_account")
                }
                continue
            
            # Check if device is connected via USB
            if device_id in usb_devices:
                available[friendly_name] = {
                    "device_id": device_id,
                    "connection_type": "usb",
                    "active_account": info.get("active_account")
                }
        
        return available
