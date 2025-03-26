"""
Step execution for Control component.
Handles executing individual steps within sequences.
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple

from ..config import Config
from ..device_manager import DeviceManager
from ..verification import ScreenVerifier, ScreenRegistry
from ..cloud import CloudClient, MessageType, Message, ProtocolConstants
from ..sandbox import SpecialSequenceRunner

class StepExecutor:
    """
    Executes individual steps within sequences.
    Implements the Singleton pattern for consistent step execution.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StepExecutor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Get configuration
        self.config = Config()
        
        # Initialize logging
        self.logger = logging.getLogger("StepExecutor")
        
        # Get required components
        self.device_manager = DeviceManager()
        self.screen_verifier = ScreenVerifier()
        self.screen_registry = ScreenRegistry()
        self.cloud_client = CloudClient()
        
        # Initialize special sequence runner
        self.special_runner = SpecialSequenceRunner()
        
        self._initialized = True
    
    def execute_step(self, workflow_id: str, device_id: str, 
                    step: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Execute individual step
        
        Args:
            workflow_id: Workflow identifier
            device_id: Device identifier
            step: Step data
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Extract step info
            step_id = step.get('step_id', '')
            step_type = step.get('type', '')
            
            # Execute step based on type
            if step_type == ProtocolConstants.ACTION_TAP:
                success, error = self._execute_tap(device_id, step)
            elif step_type == ProtocolConstants.ACTION_SWIPE:
                success, error = self._execute_swipe(device_id, step)
            elif step_type == ProtocolConstants.ACTION_TEXT:
                success, error = self._execute_text(device_id, step)
            elif step_type == ProtocolConstants.ACTION_KEY:
                success, error = self._execute_key(device_id, step)
            elif step_type == ProtocolConstants.ACTION_SPECIAL:
                success, error = self._execute_special(workflow_id, device_id, step)
            else:
                self.logger.error(f"Unknown step type: {step_type}")
                return False, f"Unknown step type: {step_type}"
            
            # Verify expected screen if specified
            if success and 'expected_screen_after' in step:
                expected_screen = step['expected_screen_after']
                timeout = step.get('verification_timeout', None)
                
                matches, screenshot = self.screen_verifier.wait_for_screen(
                    device_id,
                    workflow_id,
                    expected_screen,
                    timeout
                )
                
                if not matches:
                    # Screen verification failed
                    self.logger.error(f"Expected screen {expected_screen} not found")
                    
                    # Send unknown screen notification
                    self._report_unknown_screen(
                        workflow_id,
                        device_id,
                        step_id,
                        expected_screen,
                        screenshot
                    )
                    
                    return False, f"Expected screen {expected_screen} not found"
            
            return success, error
            
        except Exception as e:
            self.logger.error(f"Error executing step: {e}")
            return False, str(e)
    
    def _execute_tap(self, device_id: str, step: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute tap step"""
        try:
            # Get coordinates
            coordinates = step.get('coordinates', [])
            if len(coordinates) != 2:
                return False, "Invalid tap coordinates"
            
            x, y = coordinates
            
            # Execute tap
            success = self.device_manager.execute_command(
                device_id,
                ['shell', f'input tap {x} {y}']
            )[0]
            
            return success, None if success else "Tap execution failed"
            
        except Exception as e:
            self.logger.error(f"Error executing tap: {e}")
            return False, str(e)
    
    def _execute_swipe(self, device_id: str, step: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute swipe step"""
        try:
            # Get coordinates and duration
            start_coordinates = step.get('start_coordinates', [])
            end_coordinates = step.get('end_coordinates', [])
            
            if len(start_coordinates) != 2 or len(end_coordinates) != 2:
                return False, "Invalid swipe coordinates"
            
            start_x, start_y = start_coordinates
            end_x, end_y = end_coordinates
            
            duration = step.get('duration', 300)  # Default 300ms
            
            # Execute swipe
            success = self.device_manager.execute_command(
                device_id,
                ['shell', f'input swipe {start_x} {start_y} {end_x} {end_y} {duration}']
            )[0]
            
            return success, None if success else "Swipe execution failed"
            
        except Exception as e:
            self.logger.error(f"Error executing swipe: {e}")
            return False, str(e)
    
    def _execute_text(self, device_id: str, step: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute text input step"""
        try:
            # Get keyboard sequence
            keyboard_sequence = step.get('keyboard_sequence', {})
            if not keyboard_sequence:
                return False, "No keyboard sequence provided"
            
            # TODO: Add keyboard client implementation for text input
            # For now, use basic ADB text input
            text = None
            sequence = keyboard_sequence.get('sequence', [])
            
            # Extract text from sequence (simplification)
            for action in sequence:
                if action.get('action') == 'type' and 'text' in action:
                    if text is None:
                        text = action['text']
                    else:
                        text += action['text']
            
            if text is None:
                return False, "No text found in keyboard sequence"
            
            # Execute text input
            success = self.device_manager.execute_command(
                device_id,
                ['shell', f'input text "{text}"']
            )[0]
            
            return success, None if success else "Text input failed"
            
        except Exception as e:
            self.logger.error(f"Error executing text input: {e}")
            return False, str(e)
    
    def _execute_key(self, device_id: str, step: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute key event step"""
        try:
            # Get key code
            keycode = step.get('keycode')
            if keycode is None:
                return False, "No keycode provided"
            
            # Execute key event
            success = self.device_manager.execute_command(
                device_id,
                ['shell', f'input keyevent {keycode}']
            )[0]
            
            return success, None if success else "Key event failed"
            
        except Exception as e:
            self.logger.error(f"Error executing key event: {e}")
            return False, str(e)
    
    def _execute_special(self, workflow_id: str, device_id: str, 
                       step: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute special sequence step"""
        try:
            # Get special sequence
            sequence_data = step.get('sequence', {})
            if not sequence_data:
                return False, "No special sequence data provided"
            
            # Execute special sequence
            success, result = self.special_runner.run_sequence(
                workflow_id,
                device_id,
                sequence_data
            )
            
            return success, None if success else f"Special sequence failed: {result}"
            
        except Exception as e:
            self.logger.error(f"Error executing special sequence: {e}")
            return False, str(e)
    
    def _report_unknown_screen(self, workflow_id: str, device_id: str,
                             step_id: str, expected_screen: str,
                             screenshot: bytes):
        """
        Report unknown screen to Cloud
        
        Args:
            workflow_id: Workflow identifier
            device_id: Device identifier
            step_id: Step identifier
            expected_screen: Expected screen ID
            screenshot: Screenshot data
        """
        try:
            # Send unknown screen message
            self.cloud_client.send_message(Message(
                type=MessageType.UNKNOWN_SCREEN,
                data={
                    'workflow_id': workflow_id,
                    'step_id': step_id,
                    'expected_screen': expected_screen,
                    'timestamp': time.time()
                },
                device_id=device_id
            ))
            
            # Send screenshot
            package_id = workflow_id
            content_id = f"unknown_screen_{int(time.time())}"
            
            self.cloud_client.send_binary(
                package_id,
                content_id,
                screenshot
            )
            
        except Exception as e:
            self.logger.error(f"Error reporting unknown screen: {e}")
