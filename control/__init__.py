"""
Control - Device Automation Agent

Control is a robust automation agent for managing and executing 
operations on multiple Android devices. It serves as the execution layer 
that interacts directly with connected phones via ADB.
"""

# Import key components for easier access
from .config import Config, ConfigError
from .device_manager import DeviceManager
from .verification import ScreenVerifier, VerificationError
from .cloud import CloudClient, CloudError
from .workflows import WorkflowExecutor, WorkflowError
from .sandbox import SpecialSequenceRunner, RecoveryScriptRunner, SandboxError
from .keyboard import KeyboardClient, KeyboardError

__version__ = "8.0.0"

__all__ = [
    'Config',
    'ConfigError',
    'DeviceManager',
    'ScreenVerifier',
    'VerificationError',
    'CloudClient',
    'CloudError',
    'WorkflowExecutor',
    'WorkflowError',
    'SpecialSequenceRunner',
    'RecoveryScriptRunner',
    'SandboxError',
    'KeyboardClient',
    'KeyboardError',
    '__version__'
]
