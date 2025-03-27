"""
Live command definitions and validation.
"""
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

class CommandType(Enum):
    """Valid live command types"""
    TAP = "tap"
    SWIPE = "swipe"
    WAKE = "wake" 
    SLEEP = "sleep"
    KEYEVENT = "keyevent"
    APP_LAUNCH = "app_launch"
    KEYBOARD_SEQUENCE = "keyboard_sequence"
    SPECIAL_SEQUENCE = "special_sequence"

class CommandError(Exception):
    """Live command errors"""
    pass

def validate_command(data: Dict[str, Any]) -> None:
    """
    Validate live command data

    Args:
        data: Command data dictionary
        
    Raises:
        CommandError: If validation fails
    """
    required_fields = {"command_id", "type"}
    if not all(field in data for field in required_fields):
        raise CommandError("Missing required fields")
    
    cmd_type = data.get("type")
    if not isinstance(cmd_type, str):
        raise CommandError("Command type must be string")
    
    try:
        cmd_type = CommandType(cmd_type)
    except ValueError:
        raise CommandError(f"Invalid command type: {cmd_type}")

    # Validate type-specific fields
    if cmd_type == CommandType.TAP:
        if "coordinates" not in data:
            raise CommandError("Tap command requires coordinates")
        coords = data["coordinates"]
        if not isinstance(coords, list) or len(coords) != 2:
            raise CommandError("Coordinates must be [x, y]")
        
    elif cmd_type == CommandType.SWIPE:
        required = {"start_coordinates", "end_coordinates"}
        if not all(field in data for field in required):
            raise CommandError("Swipe command requires start/end coordinates")
        
    elif cmd_type == CommandType.KEYEVENT:
        if "keycode" not in data:
            raise CommandError("Keyevent command requires keycode")
        
    elif cmd_type == CommandType.APP_LAUNCH:
        if "package" not in data:
            raise CommandError("App launch command requires package name")
        
    elif cmd_type == CommandType.KEYBOARD_SEQUENCE:
        if "sequence" not in data:
            raise CommandError("Keyboard sequence command requires sequence")
        
    elif cmd_type == CommandType.SPECIAL_SEQUENCE:
        required = {"code"}
        if not all(field in data for field in required):
            raise CommandError("Special sequence requires code")
