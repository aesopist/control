"""
Keyboard integration package for Control component.
Handles communication with the custom keyboard app.
"""

from .client import KeyboardClient
from .sequence import KeyboardSequence

__all__ = [
    'KeyboardClient',
    'KeyboardSequence',
    'KeyboardError'
]

class KeyboardError(Exception):
    """Keyboard communication errors."""
    pass
