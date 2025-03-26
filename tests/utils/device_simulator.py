"""
Device simulator for testing Control component.
Simulates Android devices by providing mock ADB responses and simulated device states.
"""

import json
import logging
import threading
import queue
import socket
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

class DeviceSimulator:
    """
    Simulates Android device for testing.
    Provides mock ADB interface and simulated device states.
    """
    
    def __init__(self, device_id: str = "test_device:5555"):
        """
        Initialize device simulator
        
        Args:
            device_id: Device identifier (IP:port or serial)
        """
        self.device_id = device_id
        self._stop_event = threading.Event()
        
        # Device state
        self._screen_state = {
            "width": 1080,
            "height": 2400,
            "orientation": "portrait",
            "current_app": "com.android.launcher",
            "current_activity": "MainActivity"
        }
        
        # Command response queue
        self._command_queue = queue.Queue()
        self._response_queue = queue.Queue()
        
        # Screenshot generation
        self._screenshots_dir = Path(__file__).parent.parent / "data" / "screenshots"
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.log_dir = Path(__file__).parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"DeviceSimulator-{device_id}")
        handler = logging.FileHandler(self.log_dir / f"device_{device_id}.log")
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
    
    def start(self):
        """Start device simulator"""
        self.logger.info(f"Starting device simulator for {self.device_id}")
        
        # Start command processing thread
        self._command_thread = threading.Thread(
            target=self._process_commands,
            daemon=True
        )
        self._command_thread.start()
    
    def stop(self):
        """Stop device simulator"""
        self.logger.info(f"Stopping device simulator for {self.device_id}")
        self._stop_event.set()
        
        if self._command_thread:
            self._command_thread.join(timeout=5)
    
    def _process_commands(self):
        """Process incoming ADB commands"""
        while not self._stop_event.is_set():
            try:
                command = self._command_queue.get(timeout=1)
                if command:
                    response = self._handle_command(command)
                    self._response_queue.put(response)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing command: {e}")
    
    def _handle_command(self, command: str) -> Tuple[int, str, str]:
        """
        Handle ADB command
        
        Args:
            command: ADB command string
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        self.logger.debug(f"Handling command: {command}")
        
        try:
            # Parse command
            parts = command.split()
            if not parts:
                return (1, "", "Empty command")
            
            # Handle different command types
            if parts[0] == "input":
                return self._handle_input_command(parts[1:])
            elif parts[0] == "screencap":
                return self._handle_screencap_command()
            elif parts[0] == "shell":
                return self._handle_shell_command(parts[1:])
            else:
                return (1, "", f"Unknown command: {parts[0]}")
                
        except Exception as e:
            self.logger.error(f"Command error: {e}")
            return (1, "", str(e))
    
    def _handle_input_command(self, args: List[str]) -> Tuple[int, str, str]:
        """Handle input commands (tap, swipe, text)"""
        if not args:
            return (1, "", "Missing input type")
            
        input_type = args[0]
        
        if input_type == "tap":
            if len(args) != 3:
                return (1, "", "Invalid tap coordinates")
            try:
                x, y = int(args[1]), int(args[2])
                self.logger.info(f"Tap at ({x}, {y})")
                return (0, "", "")
            except ValueError:
                return (1, "", "Invalid tap coordinates")
                
        elif input_type == "swipe":
            if len(args) < 5:
                return (1, "", "Invalid swipe coordinates")
            try:
                x1, y1 = int(args[1]), int(args[2])
                x2, y2 = int(args[3]), int(args[4])
                duration = int(args[5]) if len(args) > 5 else 300
                self.logger.info(f"Swipe from ({x1}, {y1}) to ({x2}, {y2})")
                return (0, "", "")
            except ValueError:
                return (1, "", "Invalid swipe coordinates")
                
        elif input_type == "text":
            if len(args) < 2:
                return (1, "", "Missing text")
            text = " ".join(args[1:])
            self.logger.info(f"Input text: {text}")
            return (0, "", "")
            
        return (1, "", f"Unknown input type: {input_type}")
    
    def _handle_screencap_command(self) -> Tuple[int, str, str]:
        """Handle screenshot capture command"""
        try:
            # Generate mock screenshot
            image = self._generate_mock_screenshot()
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            
            return (0, img_bytes.getvalue().hex(), "")
            
        except Exception as e:
            return (1, "", f"Screenshot error: {e}")
    
    def _handle_shell_command(self, args: List[str]) -> Tuple[int, str, str]:
        """Handle shell commands"""
        if not args:
            return (1, "", "Missing shell command")
            
        command = args[0]
        
        if command == "dumpsys":
            # Handle dumpsys commands
            if len(args) < 2:
                return (1, "", "Missing dumpsys argument")
                
            if args[1] == "window":
                return (0, json.dumps(self._screen_state), "")
                
            return (1, "", f"Unknown dumpsys command: {args[1]}")
            
        elif command == "am":
            # Handle activity manager commands
            if len(args) < 2:
                return (1, "", "Missing am argument")
                
            if args[1] == "start":
                # Update current app/activity
                self._screen_state["current_app"] = args[2]
                self._screen_state["current_activity"] = args[3]
                return (0, "", "")
                
            return (1, "", f"Unknown am command: {args[1]}")
            
        return (1, "", f"Unknown shell command: {command}")
    
    def _generate_mock_screenshot(self) -> Image:
        """
        Generate mock screenshot
        
        Returns:
            PIL Image object
        """
        # Create blank image
        width = self._screen_state["width"]
        height = self._screen_state["height"]
        image = Image.new('RGB', (width, height), color='white')
        
        # Add some visual elements
        draw = ImageDraw.Draw(image)
        
        # Draw app name
        app_name = self._screen_state["current_app"]
        draw.text((10, 10), f"App: {app_name}", fill='black')
        
        # Draw activity name
        activity = self._screen_state["current_activity"]
        draw.text((10, 30), f"Activity: {activity}", fill='black')
        
        # Draw timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        draw.text((10, 50), f"Time: {timestamp}", fill='black')
        
        return image
    
    def execute_command(self, command: str, timeout: Optional[float] = None) -> Tuple[int, str, str]:
        """
        Execute ADB command
        
        Args:
            command: Command string
            timeout: Optional timeout in seconds
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        self._command_queue.put(command)
        try:
            return self._response_queue.get(timeout=timeout)
        except queue.Empty:
            return (1, "", "Command timeout")
    
    def set_screen_state(self, **kwargs):
        """
        Update screen state
        
        Args:
            **kwargs: State parameters to update
        """
        self._screen_state.update(kwargs)
    
    def get_screen_state(self) -> Dict[str, Any]:
        """
        Get current screen state
        
        Returns:
            Screen state dictionary
        """
        return self._screen_state.copy()
