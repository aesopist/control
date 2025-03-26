"""
Workflow package builder for testing Control component.
Helps create test workflow packages that match the expected format from Cloud.
"""

import json
import uuid
import base64
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class WorkflowBuilder:
    """
    Builds workflow packages for testing Control component.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize workflow builder
        
        Args:
            encryption_key: Optional encryption key for package encryption
        """
        self.encryption_key = encryption_key
        self.test_data_dir = Path(__file__).parent.parent / "data"
        
    def create_workflow_package(
        self,
        device_id: str,
        sequences: List[Dict[str, Any]],
        screen_registry: Optional[Dict[str, Any]] = None,
        media_files: Optional[List[str]] = None,
        encrypt: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a workflow package
        
        Args:
            device_id: Target device identifier
            sequences: List of sequence definitions
            screen_registry: Optional screen registry data
            media_files: Optional list of media file paths
            encrypt: Whether to encrypt the package
            **kwargs: Additional workflow options
            
        Returns:
            Complete workflow package
        """
        # Generate IDs
        package_id = str(uuid.uuid4())
        workflow_id = str(uuid.uuid4())
        
        # Create base workflow
        workflow = {
            "workflow_id": workflow_id,
            "name": kwargs.get("name", "Test Workflow"),
            "client_id": kwargs.get("client_id", "test_client"),
            "priority": kwargs.get("priority", 1),
            "sequences": sequences
        }
        
        if "conditional_logic" in kwargs:
            workflow["conditional_logic"] = kwargs["conditional_logic"]
        
        # Create package
        package = {
            "package_type": "workflow",
            "package_id": package_id,
            "workflow": workflow,
            "screen_registry": screen_registry or {},
            "media_files": media_files or [],
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_options": {
                "retry_count": kwargs.get("retry_count", 3),
                "debug_mode": kwargs.get("debug_mode", False)
            }
        }
        
        # Encrypt if requested
        if encrypt:
            if not self.encryption_key:
                raise ValueError("Encryption key required for encrypted packages")
            return self._encrypt_package(package)
            
        return package
    
    def create_live_command(
        self,
        device_id: str,
        command_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a live command package
        
        Args:
            device_id: Target device identifier
            command_type: Type of command (tap, swipe, etc.)
            **kwargs: Command-specific parameters
            
        Returns:
            Live command package
        """
        package_id = str(uuid.uuid4())
        command_id = str(uuid.uuid4())
        
        command = {
            "command_id": command_id,
            "type": command_type,
            "verify_screen": kwargs.get("verify_screen", False),
            "return_screenshot": kwargs.get("return_screenshot", True)
        }
        
        # Add command-specific parameters
        if command_type == "tap":
            command["coordinates"] = kwargs["coordinates"]
        elif command_type == "swipe":
            command["start_coordinates"] = kwargs["start_coordinates"]
            command["end_coordinates"] = kwargs["end_coordinates"]
            command["duration"] = kwargs.get("duration", 300)
        elif command_type == "text":
            command["keyboard_sequence"] = kwargs["keyboard_sequence"]
        
        return {
            "package_type": "live_command",
            "package_id": package_id,
            "command": command,
            "device_id": device_id,
            "session_id": kwargs.get("session_id", str(uuid.uuid4())),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def create_special_sequence(
        self,
        device_id: str,
        code: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a special sequence package
        
        Args:
            device_id: Target device identifier
            code: Python code for the sequence
            parameters: Optional parameters for the sequence
            **kwargs: Additional options
            
        Returns:
            Special sequence package
        """
        package_id = str(uuid.uuid4())
        sequence_id = str(uuid.uuid4())
        
        return {
            "package_type": "special_sequence",
            "package_id": package_id,
            "sequence": {
                "sequence_id": sequence_id,
                "name": kwargs.get("name", "Test Special Sequence"),
                "code": code,
                "parameters": parameters or {}
            },
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def create_recovery_script(
        self,
        device_id: str,
        workflow_id: str,
        code: str,
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a recovery script package
        
        Args:
            device_id: Target device identifier
            workflow_id: Original workflow ID
            code: Python code with embedded API keys
            context: Recovery context (last screen, failed step, etc.)
            **kwargs: Additional options
            
        Returns:
            Recovery script package
        """
        package_id = str(uuid.uuid4())
        script_id = str(uuid.uuid4())
        
        return {
            "package_type": "recovery_script",
            "package_id": package_id,
            "script": {
                "script_id": script_id,
                "workflow_id": workflow_id,
                "code": code,
                "context": context
            },
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def create_tap_sequence(
        self,
        coordinates_list: List[List[int]],
        expected_screens: Optional[List[str]] = None,
        verification_timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Create a sequence of tap steps
        
        Args:
            coordinates_list: List of [x, y] coordinates
            expected_screens: Optional list of expected screen IDs
            verification_timeout: Timeout for screen verification
            
        Returns:
            Sequence definition
        """
        sequence_id = str(uuid.uuid4())
        steps = []
        
        for i, coords in enumerate(coordinates_list):
            step = {
                "step_id": f"{sequence_id}_step_{i}",
                "type": "tap",
                "coordinates": coords,
                "verification_timeout": verification_timeout
            }
            if expected_screens and i < len(expected_screens):
                step["expected_screen_after"] = expected_screens[i]
            steps.append(step)
        
        return {
            "sequence_id": sequence_id,
            "name": "Tap Sequence",
            "expected_screens": expected_screens or [],
            "steps": steps
        }
    
    def create_text_sequence(
        self,
        text: str,
        delay_after: float = 0.2,
        expected_screen: Optional[str] = None,
        verification_timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Create a text input sequence
        
        Args:
            text: Text to type
            delay_after: Delay after typing
            expected_screen: Optional expected screen ID
            verification_timeout: Timeout for screen verification
            
        Returns:
            Sequence definition
        """
        sequence_id = str(uuid.uuid4())
        
        return {
            "sequence_id": sequence_id,
            "name": "Text Sequence",
            "expected_screens": [expected_screen] if expected_screen else [],
            "steps": [{
                "step_id": f"{sequence_id}_step_0",
                "type": "text",
                "keyboard_sequence": {
                    "sequence": [
                        {"action": "type", "text": text, "delay_after": delay_after}
                    ]
                },
                "expected_screen_after": expected_screen,
                "verification_timeout": verification_timeout
            }]
        }
    
    def _encrypt_package(self, package: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt a package
        
        Args:
            package: Package to encrypt
            
        Returns:
            Encrypted package data
            
        Raises:
            ValueError: If encryption fails
        """
        try:
            # Generate salt
            salt = os.urandom(16)
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits
                salt=salt,
                iterations=100000
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
            
            # Encrypt content
            f = Fernet(key)
            content = json.dumps(package).encode()
            encrypted_content = f.encrypt(content)
            
            return {
                "encrypted": True,
                "salt": base64.b64encode(salt).decode(),
                "content": base64.b64encode(encrypted_content).decode(),
                "package_id": package["package_id"]  # Include package_id in encrypted result
            }
            
        except Exception as e:
            raise ValueError(f"Package encryption failed: {e}")
    
    def _decrypt_package(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt a package
        
        Args:
            encrypted_data: Encrypted package data
            
        Returns:
            Decrypted package data
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            # Get encryption key from config
            encryption_key = self.encryption_key
            if not encryption_key:
                raise ValueError("Workflow encryption key not configured")
            
            # Get salt and encrypted content
            salt = base64.b64decode(encrypted_data.get('salt', ''))
            encrypted_content = base64.b64decode(encrypted_data.get('content', ''))
            
            if not salt or not encrypted_content:
                raise ValueError("Missing salt or encrypted content")
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
            
            # Decrypt content
            f = Fernet(key)
            decrypted_data = f.decrypt(encrypted_content)
            
            # Parse JSON content
            return json.loads(decrypted_data)
            
        except Exception as e:
            raise ValueError(f"Package decryption failed: {e}")
    
    def load_test_workflow(self, name: str) -> Dict[str, Any]:
        """
        Load a predefined test workflow
        
        Args:
            name: Name of the test workflow file
            
        Returns:
            Workflow package
            
        Raises:
            FileNotFoundError: If workflow file not found
        """
        workflow_file = self.test_data_dir / "workflows" / f"{name}.json"
        if not workflow_file.exists():
            raise FileNotFoundError(f"Test workflow not found: {name}")
            
        with open(workflow_file) as f:
            return json.load(f)
    
    def save_test_workflow(self, name: str, package: Dict[str, Any]):
        """
        Save a workflow package as a test workflow
        
        Args:
            name: Name to save as
            package: Workflow package to save
        """
        workflow_file = self.test_data_dir / "workflows" / f"{name}.json"
        workflow_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(workflow_file, 'w') as f:
            json.dump(package, f, indent=2)
