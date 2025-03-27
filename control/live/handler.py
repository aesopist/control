"""
Live command handler for Control component.
"""

import logging
from typing import Dict, Any, Tuple, Optional

from ..config import Config
from ..device_manager import DeviceManager
from ..keyboard import KeyboardClient
from ..sandbox import SpecialSequenceRunner
from ..cloud import CloudClient, MessageType, Message
from .commands import CommandType, validate_command, CommandError

class LiveCommandHandler:
    """Handles execution of live commands. Implements the Singleton pattern for consistent command handling."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LiveCommandHandler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        # Get configuration
        self.config = Config()
        
        # Initialize logging
        self.logger = logging.getLogger("LiveCommandHandler")
        
        # Get required components
        self.device_manager = DeviceManager()
        self.keyboard_client = KeyboardClient()
        self.special_runner = SpecialSequenceRunner()
        self.cloud_client = CloudClient()
        
        self._initialized = True

    def handle_command(self, message: Message) -> None:
        """Handle live command message"""
        try:
            # Extract command info
            command = message.data.get("command", {})
            device_id = message.data.get("device_id")
            session_id = message.data.get("session_id")
            
            if not command or not device_id or not session_id:
                raise CommandError("Missing required message fields")
                
            # Validate command
            validate_command(command)
            
            # Execute command
            success, error = self._execute_command(device_id, command)
            
            # Always capture screenshot after command
            screenshot = self.device_manager.capture_screenshot(device_id)
            
            # Send result with command/session correlation
            self.cloud_client.send_message(Message(
                type=MessageType.RESULT,
                data={
                    "command_id": command["command_id"],
                    "session_id": session_id,
                    "success": success,
                    "error": error
                }
            ))
            
            if screenshot:
                # Send screenshot with correlation IDs
                self.cloud_client.send_binary(
                    message.package_id,
                    f"screenshot_{command['command_id']}",
                    screenshot
                )
            
        except Exception as e:
            self.logger.error(f"Error handling live command: {e}")
            self.cloud_client.send_message(Message(
                type=MessageType.ERROR,
                data={
                    "command_id": command.get("command_id", "unknown"),
                    "session_id": session_id,
                    "error": str(e)
                }
            ))

    def _execute_command(self, device_id: str, command: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute live command"""
        try:
            cmd_type = CommandType(command["type"])
            
            if cmd_type == CommandType.TAP:
                x, y = command["coordinates"]
                success = self.device_manager.command.tap(device_id, x, y)
                return success, None if success else "Tap failed"
                
            elif cmd_type == CommandType.SWIPE:
                start_x, start_y = command["start_coordinates"]
                end_x, end_y = command["end_coordinates"]
                duration = command.get("duration", 300)
                success = self.device_manager.command.swipe(
                    device_id, start_x, start_y, end_x, end_y, duration
                )
                return success, None if success else "Swipe failed"
                
            elif cmd_type == CommandType.WAKE:
                success = self.device_manager.command.wake_device(device_id)
                return success, None if success else "Wake failed"
                
            elif cmd_type == CommandType.SLEEP:
                success = self.device_manager.command.sleep_device(device_id)
                return success, None if success else "Sleep failed"
                
            elif cmd_type == CommandType.KEYEVENT:
                success = self.device_manager.command.key_event(device_id, command["keycode"])
                return success, None if success else "Keyevent failed"
                
            elif cmd_type == CommandType.APP_LAUNCH:
                success = self.device_manager.execute_command(
                    device_id,
                    ["shell", "am", "start", "-n", command["package"]]
                )[0]
                return success, None if success else "App launch failed"
                
            elif cmd_type == CommandType.KEYBOARD_SEQUENCE:
                result = self.keyboard_client.execute_sequence(device_id, command["sequence"])
                success = result.get("status") == "success"
                return success, None if success else result.get("message", "Keyboard sequence failed")
                
            elif cmd_type == CommandType.SPECIAL_SEQUENCE:
                success, result = self.special_runner.run_sequence(None, device_id, {
                    "code": command["code"],
                    "parameters": command.get("parameters", {})
                })
                return success, None if success else f"Special sequence failed: {result}"
                
            else:
                return False, f"Unhandled command type: {cmd_type}"
                
        except Exception as e:
            return False, str(e)
