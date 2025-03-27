#!/usr/bin/env python
"""
Swipe Utility Module

Generates realistic human-like swipe events for Android devices.
This module implements natural swipe formulas based on statistical analysis
of real human touch gestures for different swipe types.
"""

import random
import math
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union

# Add the project root to the path so we can import core_device_ops
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.core_device_ops import CoreDeviceOps

# Constants for coordinate system conversion
X_FACTOR = 0.2637  # Convert from pixel to raw sensor coordinates (X)
Y_FACTOR = 0.5859  # Convert from pixel to raw sensor coordinates (Y)

# Swipe type constants
DIRECTION_UP = "up"
DIRECTION_DOWN = "down"
DIRECTION_LEFT = "left"
DIRECTION_RIGHT = "right"

SPEED_SLOW = "slow"
SPEED_FAST = "fast"

LENGTH_SHORT = "short"
LENGTH_LONG = "long"

# Swipe parameters based on statistical analysis

# 1. Slow Short Up Swipe
SLOW_SHORT_UP_DURATION_MEAN = 467
SLOW_SHORT_UP_DURATION_STD = 94
SLOW_SHORT_UP_DURATION_MIN = 257
SLOW_SHORT_UP_DURATION_MAX = 710
SLOW_SHORT_UP_DISTANCE_MEAN = 328
SLOW_SHORT_UP_DISTANCE_STD = 50
SLOW_SHORT_UP_DISTANCE_MIN = 242
SLOW_SHORT_UP_DISTANCE_MAX = 446
SLOW_SHORT_UP_DEVIATION_MEAN = 0.0548

# 2. Slow Short Down Swipe
SLOW_SHORT_DOWN_DURATION_MEAN = 491
SLOW_SHORT_DOWN_DURATION_STD = 68
SLOW_SHORT_DOWN_DURATION_MIN = 334
SLOW_SHORT_DOWN_DURATION_MAX = 626
SLOW_SHORT_DOWN_DISTANCE_MEAN = 312
SLOW_SHORT_DOWN_DISTANCE_STD = 32
SLOW_SHORT_DOWN_DISTANCE_MIN = 239
SLOW_SHORT_DOWN_DISTANCE_MAX = 376
SLOW_SHORT_DOWN_DEVIATION_MEAN = 0.0435

# 3. Slow Long Up Swipe
SLOW_LONG_UP_DURATION_MEAN = 406
SLOW_LONG_UP_DURATION_STD = 145
SLOW_LONG_UP_DURATION_MIN = 133
SLOW_LONG_UP_DURATION_MAX = 700
SLOW_LONG_UP_DISTANCE_MEAN = 1827
SLOW_LONG_UP_DISTANCE_STD = 341
SLOW_LONG_UP_DISTANCE_MIN = 1075
SLOW_LONG_UP_DISTANCE_MAX = 2449
SLOW_LONG_UP_DEVIATION_MEAN = 0.0658

# 4. Slow Long Down Swipe
SLOW_LONG_DOWN_DURATION_MEAN = 457
SLOW_LONG_DOWN_DURATION_STD = 91
SLOW_LONG_DOWN_DURATION_MIN = 275
SLOW_LONG_DOWN_DURATION_MAX = 659
SLOW_LONG_DOWN_DISTANCE_MEAN = 1898
SLOW_LONG_DOWN_DISTANCE_STD = 329
SLOW_LONG_DOWN_DISTANCE_MIN = 1239
SLOW_LONG_DOWN_DISTANCE_MAX = 2553
SLOW_LONG_DOWN_DEVIATION_MEAN = 0.0388

# 5. Fast Short Up Flick
FAST_SHORT_UP_DURATION_MEAN = 83
FAST_SHORT_UP_DURATION_STD = 10
FAST_SHORT_UP_DURATION_MIN = 60
FAST_SHORT_UP_DURATION_MAX = 102
FAST_SHORT_UP_DISTANCE_MEAN = 264
FAST_SHORT_UP_DISTANCE_STD = 96
FAST_SHORT_UP_DISTANCE_MIN = 71
FAST_SHORT_UP_DISTANCE_MAX = 495
FAST_SHORT_UP_DEVIATION_MEAN = 0.0340

# 6. Fast Short Down Flick
FAST_SHORT_DOWN_DURATION_MEAN = 93
FAST_SHORT_DOWN_DURATION_STD = 10
FAST_SHORT_DOWN_DURATION_MIN = 75
FAST_SHORT_DOWN_DURATION_MAX = 117
FAST_SHORT_DOWN_DISTANCE_MEAN = 326
FAST_SHORT_DOWN_DISTANCE_STD = 72
FAST_SHORT_DOWN_DISTANCE_MIN = 167
FAST_SHORT_DOWN_DISTANCE_MAX = 503
FAST_SHORT_DOWN_DEVIATION_MEAN = 0.0232

# 7. Fast Long Up Flick
FAST_LONG_UP_DURATION_MEAN = 79
FAST_LONG_UP_DURATION_STD = 16
FAST_LONG_UP_DURATION_MIN = 41
FAST_LONG_UP_DURATION_MAX = 117
FAST_LONG_UP_DISTANCE_MEAN = 1341
FAST_LONG_UP_DISTANCE_STD = 431
FAST_LONG_UP_DISTANCE_MIN = 464
FAST_LONG_UP_DISTANCE_MAX = 2427
FAST_LONG_UP_DEVIATION_MEAN = 0.0485

# 8. Fast Long Down Flick
FAST_LONG_DOWN_DURATION_MEAN = 57
FAST_LONG_DOWN_DURATION_STD = 10
FAST_LONG_DOWN_DURATION_MIN = 33
FAST_LONG_DOWN_DURATION_MAX = 85
FAST_LONG_DOWN_DISTANCE_MEAN = 1802
FAST_LONG_DOWN_DISTANCE_STD = 348
FAST_LONG_DOWN_DISTANCE_MIN = 975
FAST_LONG_DOWN_DISTANCE_MAX = 2567
FAST_LONG_DOWN_DEVIATION_MEAN = 0.0638

# 9. Left Swipe
LEFT_DURATION_MEAN = 105
LEFT_DURATION_STD = 13
LEFT_DURATION_MIN = 75
LEFT_DURATION_MAX = 144
LEFT_DISTANCE_MEAN = 979
LEFT_DISTANCE_STD = 304
LEFT_DISTANCE_MIN = 446
LEFT_DISTANCE_MAX = 1706
LEFT_DEVIATION_MEAN = 0.0057

# 10. Right Swipe
RIGHT_DURATION_MEAN = 130
RIGHT_DURATION_STD = 25
RIGHT_DURATION_MIN = 77
RIGHT_DURATION_MAX = 184
RIGHT_DISTANCE_MEAN = 1245
RIGHT_DISTANCE_STD = 252
RIGHT_DISTANCE_MIN = 689
RIGHT_DISTANCE_MAX = 1900
RIGHT_DEVIATION_MEAN = 0.0092


def generate_swipe_events(
    device_id: str,
    region: List[int],
    direction: str,
    speed: str = SPEED_SLOW,
    length: str = LENGTH_SHORT,
    use_core_ops: bool = True
) -> Union[bool, List[Dict[str, Any]]]:
    """
    Generate and optionally execute a realistic human-like swipe within the specified region.
    
    Args:
        device_id: ADB device ID (e.g., 192.168.1.201:5555)
        region: [x_min, y_min, x_max, y_max] region to swipe within
        direction: Direction of swipe (up, down, left, right)
        speed: Speed of swipe (slow, fast)
        length: Length of swipe (short, long) - only applicable for vertical swipes
        use_core_ops: Whether to use CoreDeviceOps to execute the events (default: True)
        
    Returns:
        If use_core_ops is True: Boolean indicating success or failure
        If use_core_ops is False: List of event dictionaries for the caller to execute
    """
    # Validate region
    if len(region) != 4:
        print(f"Invalid region: {region}. Expected [x_min, y_min, x_max, y_max]")
        return False if use_core_ops else []
    
    x_min, y_min, x_max, y_max = region
    
    # Validate coordinates
    if x_min >= x_max or y_min >= y_max:
        print(f"Invalid region: {region}. Min values must be less than max values.")
        return False if use_core_ops else []
    
    # Validate direction
    if direction not in [DIRECTION_UP, DIRECTION_DOWN, DIRECTION_LEFT, DIRECTION_RIGHT]:
        print(f"Invalid direction: {direction}. Expected one of: up, down, left, right")
        return False if use_core_ops else []
    
    # Validate speed
    if speed not in [SPEED_SLOW, SPEED_FAST]:
        print(f"Invalid speed: {speed}. Expected one of: slow, fast")
        return False if use_core_ops else []
    
    # Validate length (only applicable for vertical swipes)
    if length not in [LENGTH_SHORT, LENGTH_LONG]:
        print(f"Invalid length: {length}. Expected one of: short, long")
        return False if use_core_ops else []
    
    # Select a random point within the region
    start_x = random.randint(x_min, x_max)
    start_y = random.randint(y_min, y_max)
    
    # Determine swipe parameters based on direction, speed, and length
    if direction == DIRECTION_UP:
        if speed == SPEED_SLOW:
            if length == LENGTH_SHORT:
                # Slow Short Up Swipe
                duration_mean = SLOW_SHORT_UP_DURATION_MEAN
                duration_std = SLOW_SHORT_UP_DURATION_STD
                duration_min = SLOW_SHORT_UP_DURATION_MIN
                duration_max = SLOW_SHORT_UP_DURATION_MAX
                distance_mean = SLOW_SHORT_UP_DISTANCE_MEAN
                distance_std = SLOW_SHORT_UP_DISTANCE_STD
                distance_min = SLOW_SHORT_UP_DISTANCE_MIN
                distance_max = SLOW_SHORT_UP_DISTANCE_MAX
                deviation_mean = SLOW_SHORT_UP_DEVIATION_MEAN
            else:
                # Slow Long Up Swipe
                duration_mean = SLOW_LONG_UP_DURATION_MEAN
                duration_std = SLOW_LONG_UP_DURATION_STD
                duration_min = SLOW_LONG_UP_DURATION_MIN
                duration_max = SLOW_LONG_UP_DURATION_MAX
                distance_mean = SLOW_LONG_UP_DISTANCE_MEAN
                distance_std = SLOW_LONG_UP_DISTANCE_STD
                distance_min = SLOW_LONG_UP_DISTANCE_MIN
                distance_max = SLOW_LONG_UP_DISTANCE_MAX
                deviation_mean = SLOW_LONG_UP_DEVIATION_MEAN
        else:  # SPEED_FAST
            if length == LENGTH_SHORT:
                # Fast Short Up Flick
                duration_mean = FAST_SHORT_UP_DURATION_MEAN
                duration_std = FAST_SHORT_UP_DURATION_STD
                duration_min = FAST_SHORT_UP_DURATION_MIN
                duration_max = FAST_SHORT_UP_DURATION_MAX
                distance_mean = FAST_SHORT_UP_DISTANCE_MEAN
                distance_std = FAST_SHORT_UP_DISTANCE_STD
                distance_min = FAST_SHORT_UP_DISTANCE_MIN
                distance_max = FAST_SHORT_UP_DISTANCE_MAX
                deviation_mean = FAST_SHORT_UP_DEVIATION_MEAN
            else:
                # Fast Long Up Flick
                duration_mean = FAST_LONG_UP_DURATION_MEAN
                duration_std = FAST_LONG_UP_DURATION_STD
                duration_min = FAST_LONG_UP_DURATION_MIN
                duration_max = FAST_LONG_UP_DURATION_MAX
                distance_mean = FAST_LONG_UP_DISTANCE_MEAN
                distance_std = FAST_LONG_UP_DISTANCE_STD
                distance_min = FAST_LONG_UP_DISTANCE_MIN
                distance_max = FAST_LONG_UP_DISTANCE_MAX
                deviation_mean = FAST_LONG_UP_DEVIATION_MEAN
    elif direction == DIRECTION_DOWN:
        if speed == SPEED_SLOW:
            if length == LENGTH_SHORT:
                # Slow Short Down Swipe
                duration_mean = SLOW_SHORT_DOWN_DURATION_MEAN
                duration_std = SLOW_SHORT_DOWN_DURATION_STD
                duration_min = SLOW_SHORT_DOWN_DURATION_MIN
                duration_max = SLOW_SHORT_DOWN_DURATION_MAX
                distance_mean = SLOW_SHORT_DOWN_DISTANCE_MEAN
                distance_std = SLOW_SHORT_DOWN_DISTANCE_STD
                distance_min = SLOW_SHORT_DOWN_DISTANCE_MIN
                distance_max = SLOW_SHORT_DOWN_DISTANCE_MAX
                deviation_mean = SLOW_SHORT_DOWN_DEVIATION_MEAN
            else:
                # Slow Long Down Swipe
                duration_mean = SLOW_LONG_DOWN_DURATION_MEAN
                duration_std = SLOW_LONG_DOWN_DURATION_STD
                duration_min = SLOW_LONG_DOWN_DURATION_MIN
                duration_max = SLOW_LONG_DOWN_DURATION_MAX
                distance_mean = SLOW_LONG_DOWN_DISTANCE_MEAN
                distance_std = SLOW_LONG_DOWN_DISTANCE_STD
                distance_min = SLOW_LONG_DOWN_DISTANCE_MIN
                distance_max = SLOW_LONG_DOWN_DISTANCE_MAX
                deviation_mean = SLOW_LONG_DOWN_DEVIATION_MEAN
        else:  # SPEED_FAST
            if length == LENGTH_SHORT:
                # Fast Short Down Flick
                duration_mean = FAST_SHORT_DOWN_DURATION_MEAN
                duration_std = FAST_SHORT_DOWN_DURATION_STD
                duration_min = FAST_SHORT_DOWN_DURATION_MIN
                duration_max = FAST_SHORT_DOWN_DURATION_MAX
                distance_mean = FAST_SHORT_DOWN_DISTANCE_MEAN
                distance_std = FAST_SHORT_DOWN_DISTANCE_STD
                distance_min = FAST_SHORT_DOWN_DISTANCE_MIN
                distance_max = FAST_SHORT_DOWN_DISTANCE_MAX
                deviation_mean = FAST_SHORT_DOWN_DEVIATION_MEAN
            else:
                # Fast Long Down Flick
                duration_mean = FAST_LONG_DOWN_DURATION_MEAN
                duration_std = FAST_LONG_DOWN_DURATION_STD
                duration_min = FAST_LONG_DOWN_DURATION_MIN
                duration_max = FAST_LONG_DOWN_DURATION_MAX
                distance_mean = FAST_LONG_DOWN_DISTANCE_MEAN
                distance_std = FAST_LONG_DOWN_DISTANCE_STD
                distance_min = FAST_LONG_DOWN_DISTANCE_MIN
                distance_max = FAST_LONG_DOWN_DISTANCE_MAX
                deviation_mean = FAST_LONG_DOWN_DEVIATION_MEAN
    elif direction == DIRECTION_LEFT:
        # Left Swipe (horizontal swipes don't have length distinction)
        duration_mean = LEFT_DURATION_MEAN
        duration_std = LEFT_DURATION_STD
        duration_min = LEFT_DURATION_MIN
        duration_max = LEFT_DURATION_MAX
        distance_mean = LEFT_DISTANCE_MEAN
        distance_std = LEFT_DISTANCE_STD
        distance_min = LEFT_DISTANCE_MIN
        distance_max = LEFT_DISTANCE_MAX
        deviation_mean = LEFT_DEVIATION_MEAN
    else:  # DIRECTION_RIGHT
        # Right Swipe (horizontal swipes don't have length distinction)
        duration_mean = RIGHT_DURATION_MEAN
        duration_std = RIGHT_DURATION_STD
        duration_min = RIGHT_DURATION_MIN
        duration_max = RIGHT_DURATION_MAX
        distance_mean = RIGHT_DISTANCE_MEAN
        distance_std = RIGHT_DISTANCE_STD
        distance_min = RIGHT_DISTANCE_MIN
        distance_max = RIGHT_DISTANCE_MAX
        deviation_mean = RIGHT_DEVIATION_MEAN
    
    # Generate duration with normal distribution
    duration_ms = random.normalvariate(duration_mean, duration_std)
    duration_ms = max(duration_min, min(duration_ms, duration_max))  # Clamp to observed range
    
    # Generate distance with normal distribution
    distance = random.normalvariate(distance_mean, distance_std)
    distance = max(distance_min, min(distance, distance_max))  # Clamp to observed range
    
    # Calculate end coordinates based on direction and distance
    if direction == DIRECTION_UP:
        # For up swipes, decrease y-coordinate
        end_y = max(y_min, start_y - distance)
        
        # Add realistic path deviation to x-coordinate
        # Up swipes typically curve "left then right"
        deviation = distance * deviation_mean
        deviation_factor = random.uniform(0.5, 1.5)  # Add some randomness to deviation
        end_x = start_x + int(deviation * deviation_factor)
        
        # Ensure end_x is within the region bounds
        end_x = max(x_min, min(end_x, x_max))
        
    elif direction == DIRECTION_DOWN:
        # For down swipes, increase y-coordinate
        end_y = min(y_max, start_y + distance)
        
        # Add realistic path deviation to x-coordinate
        # Down swipes typically curve "right then left"
        deviation = distance * deviation_mean
        deviation_factor = random.uniform(0.5, 1.5)  # Add some randomness to deviation
        end_x = start_x - int(deviation * deviation_factor)
        
        # Ensure end_x is within the region bounds
        end_x = max(x_min, min(end_x, x_max))
        
    elif direction == DIRECTION_LEFT:
        # For left swipes, decrease x-coordinate
        end_x = max(x_min, start_x - distance)
        
        # Add realistic path deviation to y-coordinate
        deviation = distance * deviation_mean
        deviation_factor = random.uniform(0.5, 1.5)  # Add some randomness to deviation
        end_y = start_y + int(deviation * deviation_factor)
        
        # Ensure end_y is within the region bounds
        end_y = max(y_min, min(end_y, y_max))
        
    else:  # DIRECTION_RIGHT
        # For right swipes, increase x-coordinate
        end_x = min(x_max, start_x + distance)
        
        # Add realistic path deviation to y-coordinate
        deviation = distance * deviation_mean
        deviation_factor = random.uniform(0.5, 1.5)  # Add some randomness to deviation
        end_y = start_y - int(deviation * deviation_factor)
        
        # Ensure end_y is within the region bounds
        end_y = max(y_min, min(end_y, y_max))
    
    # If not using CoreDeviceOps, return the event parameters
    if not use_core_ops:
        return [{
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "duration_ms": int(duration_ms)
        }]
    
    # Initialize CoreDeviceOps
    core_ops = CoreDeviceOps(device_id)
    
    # Use input swipe command to execute the swipe
    cmd = f"input swipe {start_x} {start_y} {end_x} {end_y} {int(duration_ms)}"
    result, _ = core_ops.execute_command(["shell", cmd])
    
    return result


if __name__ == "__main__":
    # This is just for testing and should not be used directly
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate realistic swipe gestures")
    parser.add_argument("--device", required=True, help="Device ID")
    parser.add_argument("--region", required=True, type=str, help="Region as x_min,y_min,x_max,y_max")
    parser.add_argument("--direction", required=True, choices=["up", "down", "left", "right"], help="Swipe direction")
    parser.add_argument("--speed", default="slow", choices=["slow", "fast"], help="Swipe speed")
    parser.add_argument("--length", default="short", choices=["short", "long"], help="Swipe length (for vertical swipes)")
    
    args = parser.parse_args()
    
    region = [int(x) for x in args.region.split(",")]
    
    result = generate_swipe_events(
        device_id=args.device,
        region=region,
        direction=args.direction,
        speed=args.speed,
        length=args.length
    )
    
    print(f"Swipe {'succeeded' if result else 'failed'}")
