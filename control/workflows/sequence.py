"""
Sequence execution for Control component.
Handles executing sequences within workflows.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple

from ..config import Config
from ..device_manager import DeviceManager
from ..verification import ScreenVerifier, ScreenRegistry
from ..cloud import CloudClient, MessageType, Message, ProtocolConstants
from .step import StepExecutor

class SequenceExecutor:
    """
    Executes sequences within workflows.
    Implements the Singleton pattern for consistent sequence execution.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SequenceExecutor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Get configuration
        self.config = Config()
        
        # Initialize logging
        self.logger = logging.getLogger("SequenceExecutor")
        
        # Get required components
        self.device_manager = DeviceManager()
        self.screen_verifier = ScreenVerifier()
        self.screen_registry = ScreenRegistry()
        self.cloud_client = CloudClient()
        self.step_executor = StepExecutor()
        
        self._initialized = True
    
    def execute_sequence(self, workflow_id: str, device_id: str, 
                        sequence: Dict[str, Any]) -> bool:
        """
        Execute sequence within workflow
        
        Args:
            workflow_id: Workflow identifier
            device_id: Device identifier
            sequence: Sequence data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract sequence info
            sequence_id = sequence.get('sequence_id', '')
            name = sequence.get('name', 'Unknown Sequence')
            steps = sequence.get('steps', [])
            
            if not steps:
                self.logger.error(f"No steps in sequence {sequence_id}")
                return False
            
            # Report sequence start
            self.cloud_client.send_message(Message(
                type=MessageType.STATUS,
                data={
                    'workflow_id': workflow_id,
                    'sequence_id': sequence_id,
                    'status': 'started',
                    'name': name
                },
                device_id=device_id
            ))
            
            # Execute steps
            for i, step in enumerate(steps):
                # Get step info
                step_id = step.get('step_id', f"step_{i}")
                
                # Report step start
                self.cloud_client.send_message(Message(
                    type=MessageType.STATUS,
                    data={
                        'workflow_id': workflow_id,
                        'sequence_id': sequence_id,
                        'step_id': step_id,
                        'status': 'started'
                    },
                    device_id=device_id
                ))
                
                # Execute step
                success, error = self.step_executor.execute_step(
                    workflow_id,
                    device_id,
                    step
                )
                
                # Report step result
                self.cloud_client.send_message(Message(
                    type=MessageType.STATUS,
                    data={
                        'workflow_id': workflow_id,
                        'sequence_id': sequence_id,
                        'step_id': step_id,
                        'status': 'completed' if success else 'failed',
                        'error': error
                    },
                    device_id=device_id
                ))
                
                if not success:
                    # Sequence failed
                    self.logger.error(f"Step {step_id} failed in sequence {sequence_id}")
                    
                    # Report sequence failure
                    self.cloud_client.send_message(Message(
                        type=MessageType.RESULT,
                        data={
                            'workflow_id': workflow_id,
                            'sequence_id': sequence_id,
                            'status': ProtocolConstants.STATUS_FAILURE,
                            'error': error or f"Step {step_id} failed"
                        },
                        device_id=device_id
                    ))
                    
                    return False
                
                # Wait between steps
                time.sleep(self.config.get('workflow.step_delay', 0.5))
            
            # All steps completed successfully
            self.cloud_client.send_message(Message(
                type=MessageType.RESULT,
                data={
                    'workflow_id': workflow_id,
                    'sequence_id': sequence_id,
                    'status': ProtocolConstants.STATUS_SUCCESS
                },
                device_id=device_id
            ))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing sequence: {e}")
            
            # Report sequence error
            self.cloud_client.send_message(Message(
                type=MessageType.RESULT,
                data={
                    'workflow_id': workflow_id,
                    'sequence_id': sequence.get('sequence_id', ''),
                    'status': ProtocolConstants.STATUS_ERROR,
                    'error': str(e)
                },
                device_id=device_id
            ))
            
            return False
    
    def handle_conditional_logic(self, workflow_id: str, device_id: str,
                               condition: Dict[str, Any]) -> str:
        """
        Handle conditional logic within workflow
        
        Args:
            workflow_id: Workflow identifier
            device_id: Device identifier
            condition: Condition data
            
        Returns:
            Target sequence ID or 'continue'
        """
        try:
            condition_id = condition.get('condition_id', '')
            condition_type = condition.get('condition_type', '')
            
            if condition_type == 'screen_match':
                # Check if screen matches expected state
                screen_id = condition.get('screen_id', '')
                
                if not screen_id:
                    self.logger.error(f"No screen ID in condition {condition_id}")
                    return condition.get('if_false', 'continue')
                
                # Verify screen
                matches, _, _, _ = self.screen_verifier.verify_screen(
                    device_id,
                    workflow_id,
                    screen_id
                )
                
                # Return target based on match result
                if matches:
                    return condition.get('if_true', 'continue')
                else:
                    return condition.get('if_false', 'continue')
                    
            else:
                self.logger.error(f"Unknown condition type: {condition_type}")
                return 'continue'
                
        except Exception as e:
            self.logger.error(f"Error handling conditional logic: {e}")
            return 'continue'