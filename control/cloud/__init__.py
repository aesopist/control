"""
Cloud communication package for Control component.
Handles WebSocket communication with Cloud relay service.
"""

from .client import CloudClient
from .protocol import MessageType, Message, ProtocolConstants
from .binary import BinaryTransfer

__all__ = [
    'CloudClient',
    'MessageType',
    'Message',
    'BinaryTransfer',
    'CloudError',
    'ProtocolConstants'
]

class CloudError(Exception):
    """Cloud communication errors."""
    pass
