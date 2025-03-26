"""
Configuration management for Control component.
Handles loading and managing configuration settings from files and environment variables.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigError(Exception):
    """Configuration related errors."""
    pass

class Config:
    """
    Manages configuration settings and API keys.
    Implements the Singleton pattern to ensure consistent configuration.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Initialize paths
        self.base_path = Path(__file__).parent.parent.parent
        self.config_path = self.base_path / "config"
        self.config_path.mkdir(exist_ok=True)
        
        # Default config file
        self.config_file = self.config_path / "default_config.json"
        
        # Initialize logging
        self.logger = logging.getLogger("Config")
        
        # Load configuration
        self._config = self._load_config()
        
        # Load API keys from environment (may be used for development/testing)
        self._api_keys = self._load_api_keys()
        
        self._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            # Check for config file
            if not self.config_file.exists():
                # Copy example config if it exists
                example_config = self.config_path / "default_config.example.json"
                if example_config.exists():
                    with open(example_config) as f:
                        config = json.load(f)
                    # Save as default config
                    with open(self.config_file, 'w') as f:
                        json.dump(config, f, indent=4)
                else:
                    # Use empty config
                    config = {}
            else:
                # Load existing config
                with open(self.config_file) as f:
                    config = json.load(f)
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
            return {}
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables"""
        api_keys = {}
        
        # Only load these for development/testing purposes
        # In production, API keys should be in the injected scripts
        for env_var in os.environ:
            if env_var.endswith('_API_KEY'):
                service = env_var[:-8].lower()
                api_keys[service] = os.environ[env_var]
        
        return api_keys
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            # Split key into parts
            parts = key.split('.')
            
            # Navigate through config
            value = self._config
            for part in parts:
                value = value[part]
                
            return value
            
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key (dot notation supported)
            value: Value to set
        """
        try:
            # Split key into parts
            parts = key.split('.')
            
            # Navigate to parent
            config = self._config
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                config = config[part]
                
            # Set value
            config[parts[-1]] = value
            
            # Save config
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Failed to set config value: {str(e)}")
            raise ConfigError(f"Failed to set config value: {str(e)}")
    
    def get_api_key(self, service: str) -> Optional[str]:
        """
        Get API key for service (development/testing use only)
        
        Args:
            service: Service name (e.g., 'openai', 'gemini')
            
        Returns:
            API key if available, None otherwise
        """
        return self._api_keys.get(service)
