"""
Workflow execution for Control component.
Handles executing workflows received from Cloud.
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import threading
from queue import Queue

from ..config import Config
from ..device_manager import DeviceManager
from ..verification import ScreenVerifier, ScreenRegistry
from ..cloud import CloudClient, MessageType, Message, ProtocolConstants
from .sequence import SequenceExecutor
from .step import StepExecutor

class WorkflowExecutor:
    """
    Executes workflows received from Cloud.
    Implements the Singleton pattern for consistent workflow execution.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WorkflowExecutor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Get configuration
        self.config = Config()
        
        # Initialize paths
        self.base_path = Path(__file__).parent.parent.parent
        self.temp_path = self.base_path / "temp" / "workflows"
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        self.logger = logging.getLogger("WorkflowExecutor")
        
        # Get required components
        self.device_manager = DeviceManager()
        self.screen_verifier = ScreenVerifier()
        self.screen_registry = ScreenRegistry()
        self.cloud_client = CloudClient()
        
        # Initialize executors
        self.sequence_executor = SequenceExecutor()
        self.step_executor = StepExecutor()
        
        # Active workflows
        self._active_workflows = {}  # workflow_id -> workflow info
        self._workflow_lock = threading.Lock()
        
        # Register message handlers
        self.cloud_client.register_callback(
            MessageType.WORKFLOW, 
            self._handle_workflow_message
        )
        
        self._initialized = True
    
    def _handle_workflow_message(self, message: Message):
        """
        Handle workflow message from Cloud
        
        Args:
            message: Workflow message
        """
        try:
            # Extract workflow information
            workflow_id = message.data.get('workflow_id')
            if not workflow_id:
                self.logger.error("No workflow ID in workflow message")
                return
                
            # Process based on action
            action = message.data.get('action', '')
            
            if action == 'start':
                # Process workflow package
                self._process_workflow_package(message.data)
            elif action == 'stop':
                # Stop workflow execution
                self._stop_workflow(workflow_id)
            else:
                self.logger.error(f"Unknown workflow action: {action}")
        except Exception as e:
            self.logger.error(f"Error handling workflow message: {e}")
            
            # Report error back to Cloud
            self.cloud_client.send_message(Message(
                type=MessageType.ERROR,
                data={
                    'workflow_id': message.data.get('workflow_id', ''),
                    'error': str(e)
                }
            ))
    
    def _process_workflow_package(self, package_data: Dict[str, Any]):
        """
        Process workflow package from Cloud
        
        Args:
            package_data: Workflow package data
        """
        workflow_id = package_data.get('workflow_id')
        workflow = package_data.get('workflow', {})
        screen_registry = package_data.get('screen_registry', {})
        device_id = package_data.get('device_id')
        
        # Validate package
        if not workflow_id or not workflow or not device_id:
            self.logger.error("Invalid workflow package")
            return
        
        # Save workflow data to temporary files
        self._save_workflow_data(workflow_id, package_data)
        
        # Set screen registry
        self.screen_registry.set_registry(workflow_id, screen_registry)
        
        # Check if device is available
        available_devices = self.device_manager.get_available_devices()
        if device_id not in available_devices:
            self.logger.error(f"Device {device_id} not available")
            
            # Report error back to Cloud
            self.cloud_client.send_message(Message(
                type=MessageType.ERROR,
                data={
                    'workflow_id': workflow_id,
                    'error': f"Device {device_id} not available"
                }
            ))
            return
        
        # Start workflow execution
        self._start_workflow(workflow_id, device_id, workflow)
    
    def _save_workflow_data(self, workflow_id: str, package_data: Dict[str, Any]):
        """
        Save workflow data to temporary files
        
        Args:
            workflow_id: Workflow identifier
            package_data: Package data
        """
        try:
            # Create workflow directory
            workflow_dir = self.temp_path / workflow_id
            workflow_dir.mkdir(parents=True, exist_ok=True)
            
            # Save workflow JSON
            workflow_file = workflow_dir / "workflow.json"
            with open(workflow_file, 'w') as f:
                json.dump(package_data.get('workflow', {}), f, indent=2)
            
            # Save screen registry JSON
            registry_file = workflow_dir / "registry.json"
            with open(registry_file, 'w') as f:
                json.dump(package_data.get('screen_registry', {}), f, indent=2)
            
            # TODO: Save media files received in binary transfers
            
        except Exception as e:
            self.logger.error(f"Error saving workflow data: {e}")
            raise
    
    def _start_workflow(self, workflow_id: str, device_id: str, workflow: Dict[str, Any]):
        """
        Start workflow execution
        
        Args:
            workflow_id: Workflow identifier
            device_id: Device identifier
            workflow: Workflow data
        """
        with self._workflow_lock:
            # Check if already running
            if workflow_id in self._active_workflows:
                self.logger.warning(f"Workflow {workflow_id} already running")
                return
            
            # Initialize workflow state
            self._active_workflows[workflow_id] = {
                'workflow_id': workflow_id,
                'device_id': device_id,
                'workflow': workflow,
                'current_sequence_index': 0,
                'status': 'running',
                'start_time': time.time(),
                'error': None
            }
        
        # Start execution thread
        thread = threading.Thread(
            target=self._execute_workflow,
            args=(workflow_id,),
            daemon=True
        )
        thread.start()
        
        # Report workflow started
        self.cloud_client.send_message(Message(
            type=MessageType.STATUS,
            data={
                'workflow_id': workflow_id,
                'status': 'started',
                'device_id': device_id
            }
        ))
    
    def _execute_workflow(self, workflow_id: str):
        """
        Execute workflow in background thread
        
        Args:
            workflow_id: Workflow identifier
        """
        try:
            # Get workflow info
            workflow_info = self._active_workflows.get(workflow_id)
            if not workflow_info:
                self.logger.error(f"Workflow {workflow_id} not found")
                return
            
            device_id = workflow_info['device_id']
            workflow = workflow_info['workflow']
            
            # Get sequences
            sequences = workflow.get('sequences', [])
            if not sequences:
                self.logger.error(f"No sequences in workflow {workflow_id}")
                self._complete_workflow(workflow_id, 'failed', "No sequences in workflow")
                return
            
            # Execute sequences
            for i, sequence in enumerate(sequences):
                # Check if workflow stopped
                if self._active_workflows.get(workflow_id, {}).get('status') != 'running':
                    self.logger.info(f"Workflow {workflow_id} stopped")
                    break
                
                # Update current sequence
                with self._workflow_lock:
                    workflow_info = self._active_workflows.get(workflow_id)
                    if workflow_info:
                        workflow_info['current_sequence_index'] = i
                
                # Execute sequence
                success = self.sequence_executor.execute_sequence(
                    workflow_id,
                    device_id,
                    sequence
                )
                
                if not success:
                    self.logger.error(f"Sequence {i} failed in workflow {workflow_id}")
                    self._complete_workflow(workflow_id, 'failed', f"Sequence {i} failed")
                    return
            
            # All sequences completed successfully
            self._complete_workflow(workflow_id, 'completed')
            
        except Exception as e:
            self.logger.error(f"Error executing workflow {workflow_id}: {e}")
            self._complete_workflow(workflow_id, 'failed', str(e))
    
    def _complete_workflow(self, workflow_id: str, status: str, error: Optional[str] = None):
        """
        Complete workflow execution
        
        Args:
            workflow_id: Workflow identifier
            status: Completion status
            error: Optional error message
        """
        try:
            # Update workflow status
            with self._workflow_lock:
                workflow_info = self._active_workflows.get(workflow_id)
                if workflow_info:
                    workflow_info['status'] = status
                    workflow_info['end_time'] = time.time()
                    if error:
                        workflow_info['error'] = error
            
            # Report completion to Cloud
            self.cloud_client.send_message(Message(
                type=MessageType.RESULT,
                data={
                    'workflow_id': workflow_id,
                    'status': status,
                    'error': error
                }
            ))
            
            # Clean up temporary files
            self._cleanup_workflow(workflow_id)
            
        except Exception as e:
            self.logger.error(f"Error completing workflow {workflow_id}: {e}")
        finally:
            # Remove from active workflows
            with self._workflow_lock:
                self._active_workflows.pop(workflow_id, None)
    
    def _stop_workflow(self, workflow_id: str):
        """
        Stop workflow execution
        
        Args:
            workflow_id: Workflow identifier
        """
        with self._workflow_lock:
            workflow_info = self._active_workflows.get(workflow_id)
            if workflow_info:
                workflow_info['status'] = 'stopping'
    
    def _cleanup_workflow(self, workflow_id: str):
        """
        Clean up workflow temporary files
        
        Args:
            workflow_id: Workflow identifier
        """
        try:
            # Remove screen registry
            self.screen_registry.remove_registry(workflow_id)
            
            # Remove workflow directory
            workflow_dir = self.temp_path / workflow_id
            if workflow_dir.exists():
                for file in workflow_dir.iterdir():
                    file.unlink()
                workflow_dir.rmdir()
                
        except Exception as e:
            self.logger.error(f"Error cleaning up workflow {workflow_id}: {e}")
    
    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """
        Get all active workflows
        
        Returns:
            List of active workflow info dictionaries
        """
        with self._workflow_lock:
            return list(self._active_workflows.values())
    
    def stop(self):
        """Stop all workflows"""
        with self._workflow_lock:
            workflow_ids = list(self._active_workflows.keys())
        
        for workflow_id in workflow_ids:
            self._stop_workflow(workflow_id)