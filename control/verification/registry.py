"""
Screen registry for Control component.
Handles storing and managing screen registries for workflows.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading

from ..config import Config

class ScreenRegistry:
    """
    Manages screen registries for workflows.
    Implements the Singleton pattern for consistent registry management.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScreenRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Get configuration
        self.config = Config()
        
        # Initialize paths
        self.base_path = Path(__file__).parent.parent.parent
        self.temp_path = self.base_path / "temp" / "registries"
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        self.logger = logging.getLogger("ScreenRegistry")
        
        # Registry storage
        self._registries = {}  # workflow_id -> registry
        self._registry_lock = threading.Lock()
        
        self._initialized = True
    
    def get_registry(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get screen registry for workflow
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Screen registry dictionary or None if not found
        """
        with self._registry_lock:
            return self._registries.get(workflow_id)
    
    def set_registry(self, workflow_id: str, registry: Dict[str, Any]) -> bool:
        """
        Set screen registry for workflow
        
        Args:
            workflow_id: Workflow identifier
            registry: Screen registry dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._registry_lock:
                self._registries[workflow_id] = registry
                
                # Save to temporary file for persistence
                self._save_registry(workflow_id, registry)
                
            return True
        except Exception as e:
            self.logger.error(f"Error setting registry for {workflow_id}: {e}")
            return False
    
    def remove_registry(self, workflow_id: str) -> bool:
        """
        Remove screen registry for workflow
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._registry_lock:
                if workflow_id in self._registries:
                    self._registries.pop(workflow_id)
                    
                    # Remove temporary file
                    registry_file = self.temp_path / f"{workflow_id}.json"
                    if registry_file.exists():
                        registry_file.unlink()
                    
            return True
        except Exception as e:
            self.logger.error(f"Error removing registry for {workflow_id}: {e}")
            return False
    
    def _save_registry(self, workflow_id: str, registry: Dict[str, Any]):
        """
        Save registry to temporary file
        
        Args:
            workflow_id: Workflow identifier
            registry: Screen registry dictionary
        """
        try:
            registry_file = self.temp_path / f"{workflow_id}.json"
            with open(registry_file, 'w') as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving registry file for {workflow_id}: {e}")
    
    def load_registry(self, workflow_id: str) -> bool:
        """
        Load registry from temporary file
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            registry_file = self.temp_path / f"{workflow_id}.json"
            if registry_file.exists():
                with open(registry_file, 'r') as f:
                    registry = json.load(f)
                
                with self._registry_lock:
                    self._registries[workflow_id] = registry
                
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Error loading registry file for {workflow_id}: {e}")
            return False
    
    def get_screen_info(self, workflow_id: str, screen_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information for specific screen
        
        Args:
            workflow_id: Workflow identifier
            screen_id: Screen identifier
            
        Returns:
            Screen information dictionary or None if not found
        """
        registry = self.get_registry(workflow_id)
        if registry and screen_id in registry:
            return registry[screen_id]
        return None
