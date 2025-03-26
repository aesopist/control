"""
Sandbox package for Control component.
Handles secure execution of injected code.
"""

from .runner import SpecialSequenceRunner, RecoveryScriptRunner

__all__ = [
    'SpecialSequenceRunner',
    'RecoveryScriptRunner',
    'SandboxError'
]

class SandboxError(Exception):
    """Sandbox execution errors."""
    pass
