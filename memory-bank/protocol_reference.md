# Protocol Reference

## Overview
This document defines the protocol used by the Control component for communication with external services. It covers message types, binary header format, error handling, and provides guidelines for future extensions via a plugin architecture.

## Message Types
- **WORKFLOW**: Used to send and receive workflow packages.
- **COMMAND**: Used to send live command packages.
- **PING / PONG**: Used for connection keepalive.
- *(Additional message types may be defined as needed.)*

## Binary Header Format
Binary messages include a header with the following fields:
- **package_id**: A 32-bit integer derived from the original package identifier.
- **content_id**: A 32-bit integer derived from the content identifier.
- **content_length**: An unsigned integer specifying the length of the binary payload.

**File Format Requirements:**  
Screenshots and image files are transmitted in PNG format, and videos in MP4 format. This avoids base64 encoding because:
- Converting to base64 adds conversion overhead.
- All key external components (APIs and services) expect data in actual file formats.
- Core modules that process images require them in PNG format for compatibility with external APIs.

## Error Handling
The protocol defines standardized error codes and response formats for:
- Invalid message formats
- Processing errors
- Unsupported operations
Error responses include a numeric code and a descriptive message to facilitate troubleshooting.

## Protocol Extensibility
A lightweight plugin architecture is supported so that new message types or modifications to existing messages can be added without breaking compatibility. This makes the protocol flexible and allows for future enhancements.

## ID Mapping (Internal)
For efficiency during binary transfers, string identifiers (such as package IDs and content identifiers) are converted to 32-bit integers using a simple hash function. An internal ID mapping table is maintained which maps these integer values back to their original string representations. This mapping is used solely for debugging and testing purposes and is not exposed to external clients.
