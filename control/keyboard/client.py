"""
Keyboard client for Control component.
Handles communication with the custom keyboard app.
"""

import logging
import json
import time
import requests
from typing import Dict, List, Optional, Any, Union

from ..config import Config

class KeyboardClient:
    """
    Communicates with the custom keyboard app via HTTP.
    Implements the Singleton pattern for consistent keyboard communication.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KeyboardClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Get configuration
        self.config = Config()
        
        # Initialize logging
        self.logger = logging.getLogger("KeyboardClient")
        
        # Default keyboard port
        self.default_port = self.config.get('keyboard.default_port', 8080)
        
        # Request timeout
        self.timeout = self.config.get('keyboard.timeout', 30)
        
        self._initialized = True
    
    def get_keyboard_address(self, device_id: str) -> Optional[str]:
        """
        Get keyboard address for device
        
        Args:
            device_id: Device identifier
            
        Returns:
            Keyboard address (ip:port) or None if not found
        """
        # Try to extract IP from device_id (for WiFi devices)
        if ":" in device_id:
            ip = device_id.split(":")[0]
            return f"{ip}:{self.default_port}"
        
        # Try to get from device config
        devices = self.config.get('devices', {})
        device_info = devices.get(device_id, {})
        
        if 'ip_address' in device_info:
            ip = device_info['ip_address']
            port = device_info.get('keyboard_port', self.default_port)
            return f"{ip}:{port}"
        
        return None
    
    def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send command to keyboard
        
        Args:
            device_id: Device identifier
            command: Command dictionary
            
        Returns:
            Response dictionary
        """
        keyboard_address = self.get_keyboard_address(device_id)
        if not keyboard_address:
            error_msg = f"No keyboard address for device {device_id}"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        try:
            url = f"http://{keyboard_address}/command"
            response = requests.post(
                url,
                json=command,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Keyboard request failed: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Keyboard communication error: {str(e)}"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}
    
    def type_text(self, device_id: str, text: str) -> Dict[str, Any]:
        """
        Type text using keyboard
        
        Args:
            device_id: Device identifier
            text: Text to type
            
        Returns:
            Response dictionary
        """
        return self.send_command(device_id, {"action": "type", "text": text})
    
    def delete_text(self, device_id: str, count: int = 1) -> Dict[str, Any]:
        """
        Delete text using keyboard
        
        Args:
            device_id: Device identifier
            count: Number of characters to delete
            
        Returns:
            Response dictionary
        """
        return self.send_command(device_id, {"action": "delete", "count": count})
    
    def get_clipboard(self, device_id: str) -> str:
        """
        Get clipboard content
        
        Args:
            device_id: Device identifier
            
        Returns:
            Clipboard text or empty string on error
        """
        response = self.send_command(device_id, {"action": "clipboard_get"})
        
        if response.get("status") == "success" and "text" in response:
            return response["text"]
        return ""
    
    def set_clipboard(self, device_id: str, text: str) -> bool:
        """
        Set clipboard content
        
        Args:
            device_id: Device identifier
            text: Text to set
            
        Returns:
            True if successful, False otherwise
        """
        response = self.send_command(device_id, {"action": "clipboard_set", "text": text})
        return response.get("status") == "success"
    
    def execute_sequence(self, device_id: str, sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute sequence of keyboard actions
        
        Args:
            device_id: Device identifier
            sequence: List of action dictionaries
            
        Returns:
            Response dictionary
        """
        return self.send_command(
            device_id, 
            {"action": "execute_sequence", "sequence": sequence}
        )