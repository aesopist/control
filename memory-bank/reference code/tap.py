#!/usr/bin/env python
"""
Tap Utility Module

Generates realistic human-like tap events for Android devices.
This module implements the natural tap formula based on statistical analysis
of real human touch gestures.
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

# Tap parameters based on statistical analysis of typing_test_1_The_quick_brown_fox.json
# Duration parameters (ms)
DURATION_MEAN = 66.47
DURATION_STD = 14.37
DURATION_MIN = 32.38
DURATION_MAX = 124.61

# Distance parameters (pixels)
DISTANCE_MEAN = 12.01
DISTANCE_STD = 9.16
DISTANCE_MIN = 0.00
DISTANCE_MAX = 48.55

# Movement vector parameters (pixels)
DX_MEAN = -1.51
DX_STD = 13.57
DY_MEAN = 0.87
DY_STD = 6.40

# Quadrant distribution for movement direction
QUADRANT_PROBS = {
    'Q1 (right-down)': 0.3006,  # +x, +y
    'Q2 (left-down)': 0.3121,   # -x, +y
    'Q3 (left-up)': 0.2197,     # -x, -y
    'Q4 (right-up)': 0.1676     # +x, -y
}

def generate_tap_events(
    device_id: str,
    region: List[int],
    input_device: str = "/dev/input/event8",
    use_core_ops: bool = True
) -> Union[bool, List[Dict[str, Any]]]:
    """
    Generate and optionally execute a realistic human-like tap within the specified region.
    
    Args:
        device_id: ADB device ID (e.g., 192.168.1.201:5555)
        region: [x_min, y_min, x_max, y_max] region to tap within
        input_device: Input device path (default: /dev/input/event8)
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
        
    # Select a random point within the region
    start_x = random.randint(x_min, x_max)
    start_y = random.randint(y_min, y_max)
    
    # Generate tap parameters based on statistical analysis
    
    # 1. Duration component (normal distribution with realistic parameters)
    duration_ms = min(max(random.normalvariate(DURATION_MEAN, DURATION_STD), DURATION_MIN), DURATION_MAX)
    
    # 2. Movement component (realistic distance and direction)
    has_movement = random.random() < 0.98  # 98% of taps had some movement
    
    # Determine end coordinates with movement
    if has_movement:
        # Select movement distance from normal distribution
        movement_distance = random.normalvariate(DISTANCE_MEAN, DISTANCE_STD)
        movement_distance = max(DISTANCE_MIN, min(movement_distance, DISTANCE_MAX))  # Clamp to observed range
        
        # Select movement direction based on quadrant probabilities
        quadrant = random.choices(
            list(QUADRANT_PROBS.keys()),
            weights=list(QUADRANT_PROBS.values())
        )[0]
        
        # Generate angle within the selected quadrant
        if quadrant == 'Q1 (right-down)':  # +x, +y
            movement_angle = random.uniform(0, math.pi/2)
        elif quadrant == 'Q2 (left-down)':  # -x, +y
            movement_angle = random.uniform(math.pi/2, math.pi)
        elif quadrant == 'Q3 (left-up)':  # -x, -y
            movement_angle = random.uniform(math.pi, 3*math.pi/2)
        else:  # Q4 (right-up): +x, -y
            movement_angle = random.uniform(3*math.pi/2, 2*math.pi)
        
        # Calculate end coordinates
        dx = movement_distance * math.cos(movement_angle)
        dy = movement_distance * math.sin(movement_angle)
        
        # Alternative approach: directly use dx/dy statistics
        if random.random() < 0.5:  # 50% chance to use direct dx/dy stats
            dx = random.normalvariate(DX_MEAN, DX_STD)
            dy = random.normalvariate(DY_MEAN, DY_STD)
        
        end_x = int(start_x + dx)
        end_y = int(start_y + dy)
    else:
        # No movement, end coordinates are the same as start
        end_x = start_x
        end_y = start_y
    
    # If not using CoreDeviceOps, return the event parameters
    if not use_core_ops:
        return [{
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "duration_ms": duration_ms
        }]
    
    # Initialize CoreDeviceOps
    core_ops = CoreDeviceOps(device_id)
    
    # Use input swipe command to simulate the tap
    # For a tap with minimal movement, we use swipe with a very short duration
    cmd = f"input swipe {start_x} {start_y} {end_x} {end_y} {int(duration_ms)}"
    result, _ = core_ops.execute_command(["shell", cmd])
    
    return result


if __name__ == "__main__":
    # This is just for testing and should not be used directly
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the tap utility")
    parser.add_argument("device_id", help="ADB device ID (e.g., 192.168.1.201:5555)")
    parser.add_argument("--region", type=int, nargs=4, default=[100, 100, 980, 1800],
                        help="Region to tap within [x_min, y_min, x_max, y_max]")
    parser.add_argument("--input-device", default="/dev/input/event8",
                        help="Input device path (default: /dev/input/event8)")
    
    args = parser.parse_args()
    
    print(f"Testing tap on device {args.device_id}")
    print(f"Tapping within region {args.region}")
    
    result = generate_tap_events(args.device_id, args.region, args.input_device)
    
    if result:
        print("Tap executed successfully")
    else:
        print("Tap execution failed")
