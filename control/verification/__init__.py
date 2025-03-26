"""
Screen verification package for Control component.
Handles verifying device screens against reference images.
"""

from .verifier import ScreenVerifier
from .comparator import ImageComparator
from .registry import ScreenRegistry

__all__ = [
    'ScreenVerifier',
    'ImageComparator',
    'ScreenRegistry',
    'VerificationError'
]

class VerificationError(Exception):
    """Screen verification errors."""
    pass
