"""
Code execution sandbox for Control component.
Handles secure execution of injected code for special sequences and recovery scripts.
"""

import logging
import tempfile
import subprocess
import sys
import os
import time
import importlib.util
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from ..config import Config

class BaseRunner:
    """
    Base class for code execution runners.
    """
    
    def __init__(self):
        # Get configuration
        self.config = Config()
        
        # Initialize paths
        self.base_path = Path(__file__).parent.parent.parent
        self.temp_path = self.base_path / "temp" / "sandbox"
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Execution timeout
        self.execution_timeout = self.config.get('sandbox.execution_timeout', 300)  # 5 minutes
    
    def _create_temp_script(self, code: str, prefix: str) -> Path:
        """
        Create temporary script file
        
        Args:
            code: Script code
            prefix: File name prefix
            
        Returns:
            Path to temporary script file
        """
        try:
            # Create a unique file name
            timestamp = int(time.time())
            script_path = self.temp_path / f"{prefix}_{timestamp}.py"
            
            # Write code to file
            with open(script_path, 'w') as f:
                f.write(code)
            
            return script_path
            
        except Exception as e:
            self.logger.error(f"Error creating temporary script: {e}")
            raise
    
    def _cleanup_temp_script(self, script_path: Path):
        """
        Clean up temporary script file
        
        Args:
            script_path: Path to temporary script file
        """
        try:
            if script_path.exists():
                script_path.unlink()
        except Exception as e:
            self.logger.error(f"Error cleaning up temporary script: {e}")
    
    def _execute_external(self, script_path: Path, timeout: Optional[int] = None) -> Tuple[bool, str]:
        """
        Execute script in external process
        
        Args:
            script_path: Path to script file
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple of (success, output)
        """
        if timeout is None:
            timeout = self.execution_timeout
            
        try:
            # Execute script in separate process
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Check result
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, f"Script execution timed out after {timeout} seconds"
        except Exception as e:
            return False, f"Error executing script: {e}"
    
    def _execute_in_memory(self, code: str, globals_dict: Dict[str, Any], 
                          timeout: Optional[int] = None) -> Tuple[bool, Any]:
        """
        Execute code in memory with timeout
        
        Args:
            code: Python code to execute
            globals_dict: Globals dictionary for execution
            timeout: Execution timeout in seconds
            
        Returns:
            Tuple of (success, result)
        """
        if timeout is None:
            timeout = self.execution_timeout
        
        # Set up result container
        result_container = {'success': False, 'result': None, 'error': None}
        execution_complete = threading.Event()
        
        # Define execution function
        def execute_code():
            try:
                # Execute code
                local_vars = {}
                exec(code, globals_dict, local_vars)
                
                # Check for return value
                result = local_vars.get('result', None)
                
                # Update result container
                result_container['success'] = True
                result_container['result'] = result
                
            except Exception as e:
                # Update result container with error
                result_container['error'] = str(e)
                
            finally:
                # Signal completion
                execution_complete.set()
        
        # Start execution thread
        thread = threading.Thread(target=execute_code, daemon=True)
        thread.start()
        
        # Wait for completion or timeout
        execution_complete.wait(timeout=timeout)
        
        if not execution_complete.is_set():
            return False, f"Execution timed out after {timeout} seconds"
            
        if result_container['success']:
            return True, result_container['result']
        else:
            return False, result_container['error']


class SpecialSequenceRunner(BaseRunner):
    """
    Handles execution of special sequence scripts.
    Implements the Singleton pattern for consistent execution.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpecialSequenceRunner, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        super().__init__()
        self.logger = logging.getLogger("SpecialSequenceRunner")
        self._initialized = True
    
    def run_sequence(self, workflow_id: str, device_id: str, 
                    sequence_data: Dict[str, Any]) -> Tuple[bool, Any]:
        """
        Run special sequence
        
        Args:
            workflow_id: Workflow identifier
            device_id: Device identifier
            sequence_data: Sequence data including code
            
        Returns:
            Tuple of (success, result)
        """
        try:
            # Get sequence code
            code = sequence_data.get('code')
            if not code:
                return False, "No code provided"
            
            # Get sequence parameters
            params = sequence_data.get('parameters', {})
            
            # Create temporary script
            script_path = self._create_temp_script(code, "special")
            
            try:
                # Set up environment variables
                env = os.environ.copy()
                env['CONTROL_DEVICE_ID'] = device_id
                env['CONTROL_WORKFLOW_ID'] = workflow_id
                
                # Add parameters as environment variables
                for key, value in params.items():
                    env[f'CONTROL_PARAM_{key.upper()}'] = str(value)
                
                # Execute script in separate process
                success, output = self._execute_external(script_path)
                
                if success:
                    return True, output
                else:
                    self.logger.error(f"Special sequence execution failed: {output}")
                    return False, output
                    
            finally:
                # Clean up
                self._cleanup_temp_script(script_path)
                
        except Exception as e:
            self.logger.error(f"Error running special sequence: {e}")
            return False, str(e)


class RecoveryScriptRunner(BaseRunner):
    """
    Handles execution of recovery scripts.
    Implements the Singleton pattern for consistent execution.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RecoveryScriptRunner, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        super().__init__()
        self.logger = logging.getLogger("RecoveryScriptRunner")
        self._initialized = True
    
    def run_recovery(self, workflow_id: str, device_id: str, 
                   script_data: Dict[str, Any]) -> Tuple[bool, Any]:
        """
        Run recovery script
        
        Args:
            workflow_id: Workflow identifier
            device_id: Device identifier
            script_data: Script data including code and context
            
        Returns:
            Tuple of (success, result)
        """
        try:
            # Get script code
            code = script_data.get('code')
            if not code:
                return False, "No code provided"
            
            # Get script context
            context = script_data.get('context', {})
            
            # Create temporary script
            script_path = self._create_temp_script(code, "recovery")
            
            try:
                # Set up environment variables
                env = os.environ.copy()
                env['CONTROL_DEVICE_ID'] = device_id
                env['CONTROL_WORKFLOW_ID'] = workflow_id
                
                # Add context as environment variables
                for key, value in context.items():
                    env[f'CONTROL_CONTEXT_{key.upper()}'] = str(value)
                
                # Execute script in separate process with longer timeout
                timeout = self.config.get('recovery.timeout', 600)  # 10 minutes
                success, output = self._execute_external(script_path, timeout)
                
                if success:
                    return True, output
                else:
                    self.logger.error(f"Recovery script execution failed: {output}")
                    return False, output
                    
            finally:
                # Clean up
                self._cleanup_temp_script(script_path)
                
        except Exception as e:
            self.logger.error(f"Error running recovery script: {e}")
            return False, str(e)