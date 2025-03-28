"""
Protocol definitions for Control-Cloud communication.
"""

from enum import Enum, auto
from typing import Dict, Type, Optional, Any, Union
import logging
import struct
import json
from dataclasses import dataclass
from typing_extensions import Protocol

class MessageType(Enum):
    """Supported message types"""
    WORKFLOW = "workflow"
    LIVE_COMMAND = "live_command"
    SPECIAL_SEQUENCE = "special_sequence"
    RECOVERY_SCRIPT = "recovery_script"
    BINARY_TRANSFER = "binary_transfer"
    BINARY = "binary"  # Added for binary message handling
    PING = "ping"
    PONG = "pong"
    RESULT = "result"
    ERROR = "error"
    STATUS = "status"
    DEVICE_LIST = "device_list"
    DEVICE_DISCONNECTED = "device_disconnected"
    CLIENT_INFO = "client_info"

class ProtocolError(Enum):
    """Protocol error codes"""
    # Message Format Errors
    INVALID_FORMAT = "invalid_format"
    MISSING_FIELD = "missing_field"
    INVALID_TYPE = "invalid_type"
    UNSUPPORTED_MESSAGE = "unsupported_message"
    
    # Binary Transfer Errors
    INVALID_HEADER = "invalid_header"
    CONTENT_MISMATCH = "content_mismatch"
    TRANSFER_INCOMPLETE = "transfer_incomplete"
    
    # Validation Errors
    SCHEMA_VIOLATION = "schema_violation"
    INVALID_SEQUENCE = "invalid_sequence"
    INVALID_STEP = "invalid_step"
    
    # Runtime Errors
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    DEVICE_ERROR = "device_error"

class ProtocolException(Exception):
    """Exception raised for protocol errors"""
    def __init__(self, error: ProtocolError, message: str, details: Optional[Dict] = None):
        self.error = error
        self.message = message
        self.details = details or {}
        super().__init__(f"{error.value}: {message}")

    def to_dict(self) -> Dict:
        """Convert to error response format"""
        return {
            "error": {
                "code": self.error.value,
                "message": self.message,
                "details": self.details
            }
        }

@dataclass
class BinaryHeader:
    """Binary message header"""
    package_id: int
    content_id: int
    content_length: int
    flags: int
    filename: str

    # Header format:
    # 4 bytes: package_id (uint32)
    # 4 bytes: content_id (uint32)
    # 4 bytes: content_length (uint32)
    # 2 bytes: flags (uint16)
    # 64 bytes: filename (string, null-padded)
    HEADER_FORMAT = "!IIIH64s"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    @classmethod
    def from_bytes(cls, header_bytes: bytes) -> 'BinaryHeader':
        """Parse header from bytes"""
        if len(header_bytes) < cls.HEADER_SIZE:
            raise ProtocolException(
                ProtocolError.INVALID_HEADER,
                f"Header too short: {len(header_bytes)} < {cls.HEADER_SIZE}"
            )

        try:
            package_id, content_id, content_length, flags, filename_bytes = struct.unpack(
                cls.HEADER_FORMAT, header_bytes[:cls.HEADER_SIZE]
            )
            # Decode filename and strip null padding
            filename = filename_bytes.decode('utf-8').rstrip('\0')
            return cls(package_id, content_id, content_length, flags, filename)
        except struct.error as e:
            raise ProtocolException(
                ProtocolError.INVALID_HEADER,
                f"Failed to parse header: {e}"
            )

    def to_bytes(self) -> bytes:
        """Convert header to bytes"""
        try:
            # Encode and pad filename
            filename_bytes = self.filename.encode('utf-8')[:64].ljust(64, b'\0')
            return struct.pack(
                self.HEADER_FORMAT,
                self.package_id,
                self.content_id,
                self.content_length,
                self.flags,
                filename_bytes
            )
        except struct.error as e:
            raise ProtocolException(
                ProtocolError.INVALID_HEADER,
                f"Failed to create header: {e}"
            )

class MessageHandler(Protocol):
    """Protocol for message handlers"""
    def validate(self, message: Dict) -> bool:
        """Validate message format"""
        ...

    def process(self, message: Dict) -> Dict:
        """Process message and return response"""
        ...

class Message:
    """Base message class"""
    def __init__(self, type: Union[MessageType, str], data: Dict, id: Optional[str] = None, device_id: Optional[str] = None):
        # Handle both MessageType enum and string
        if isinstance(type, str):
            try:
                self.type = MessageType(type)
            except ValueError:
                # If not a valid enum value, store as is but log a warning
                self.type = type
                logging.getLogger("Message").warning(f"Unknown message type: {type}")
        else:
            self.type = type
            
        self.data = data
        self.id = id
        self.device_id = device_id
        self.content = data  # Alias data as content for backward compatibility

    @property
    def package_type(self) -> str:
        """Get package type from content"""
        return self.data.get("package_type", "")

    @property
    def package_id(self) -> str:
        """Get package ID from content"""
        return self.data.get("package_id", "")

    def validate(self) -> bool:
        """Validate message content"""
        if not isinstance(self.content, dict):
            raise ProtocolException(
                ProtocolError.INVALID_FORMAT,
                "Message content must be a dictionary"
            )
        if "package_type" not in self.content:
            raise ProtocolException(
                ProtocolError.MISSING_FIELD,
                "Message must have package_type"
            )
        if "package_id" not in self.content:
            raise ProtocolException(
                ProtocolError.MISSING_FIELD,
                "Message must have package_id"
            )
        return True

class Protocol:
    """Protocol implementation"""
    def __init__(self):
        self._handlers: Dict[MessageType, MessageHandler] = {}

    def register_handler(self, message_type: MessageType, handler: MessageHandler) -> None:
        """Register a message handler"""
        self._handlers[message_type] = handler

    def process_message(self, message: Dict) -> Dict:
        """Process a message"""
        try:
            # Validate basic message structure
            if not isinstance(message, dict):
                raise ProtocolException(
                    ProtocolError.INVALID_FORMAT,
                    "Message must be a dictionary"
                )

            # Get message type
            package_type = message.get("package_type")
            if not package_type:
                raise ProtocolException(
                    ProtocolError.MISSING_FIELD,
                    "Message must have package_type"
                )

            try:
                message_type = MessageType(package_type)
            except ValueError:
                raise ProtocolException(
                    ProtocolError.UNSUPPORTED_MESSAGE,
                    f"Unsupported message type: {package_type}"
                )

            # Get handler
            handler = self._handlers.get(message_type)
            if not handler:
                raise ProtocolException(
                    ProtocolError.UNSUPPORTED_MESSAGE,
                    f"No handler for message type: {message_type.value}"
                )

            # Validate and process
            if not handler.validate(message):
                raise ProtocolException(
                    ProtocolError.SCHEMA_VIOLATION,
                    "Message failed validation"
                )

            return handler.process(message)

        except ProtocolException as e:
            return e.to_dict()
        except Exception as e:
            return ProtocolException(
                ProtocolError.EXECUTION_ERROR,
                str(e)
            ).to_dict()

class ProtocolConstants:
    """Protocol constants used across the system"""
    # Message Types
    STATUS = "status"      # Status updates
    ERROR = "error"        # Error messages
    RESULT = "result"      # Operation results
    
    # Package Types
    WORKFLOW = "workflow"
    LIVE_COMMAND = "live_command"
    SPECIAL_SEQUENCE = "special_sequence"
    RECOVERY_SCRIPT = "recovery_script"
    BINARY_TRANSFER = "binary_transfer"

    # Actions
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"

    # Status Values
    STARTED = "started"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    
    # New constants for step types
    ACTION_TAP = "tap"
    ACTION_SWIPE = "swipe"
    ACTION_TEXT = "text"
    ACTION_KEY = "key"
    ACTION_SPECIAL = "special"
    
    # New constants for execution status
    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "failed"
    STATUS_ERROR = "error"
