"""
Screen verification for Control component.
Handles verifying device screens against reference images in workflow packages.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from ..config import Config
from ..device_manager import DeviceManager
from .comparator import ImageComparator

class ScreenVerifier:
    """
    Verifies device screens against references from workflow packages.
    Implements the Singleton pattern for consistent verification.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScreenVerifier, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Get configuration
        self.config = Config()
        
        # Initialize paths
        self.base_path = Path(__file__).parent.parent.parent
        self.temp_path = self.base_path / "temp" / "screenshots"
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        self.logger = logging.getLogger("ScreenVerifier")
        
        # Get device manager
        self.device_manager = DeviceManager()
        
        # Initialize image comparator
        self.comparator = ImageComparator()
        
        # Default settings: use MSE threshold (lower is better). 1000 is the proven acceptable value.
        self.match_threshold = self.config.get('screen.mse_threshold', 1000)
        self.verification_timeout = self.config.get('workflow.verification_timeout', 10)
        
        self._initialized = True
    
    def verify_screen(self, device_id: str, 
                      expected_screen_id: str,
                      ref_image_path: str,
                      validation_regions: List[Dict[str, int]]) -> Tuple[bool, float, bytes]:
        """
        Verify current device screen against expected screen.
        
        Args:
            device_id: Device identifier
            expected_screen_id: Expected screen ID
            ref_image_path: Path to reference image
            validation_regions: List of validation region dictionaries
            
        Returns:
            Tuple of (matches, match_score, screenshot_data)
        """
        try:
            # Get screenshot
            screenshot_data = self.device_manager.capture_screenshot(device_id)
            
            if screenshot_data is None:
                self.logger.error(f"Failed to capture screenshot for {device_id}")
                return False, 0.0, b''
            
            # Convert screenshot to numpy array
            np_array = np.frombuffer(screenshot_data, dtype=np.uint8)
            screenshot = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
            
            if screenshot is None:
                self.logger.error(f"Failed to decode screenshot for {device_id}")
                return False, 0.0, screenshot_data
            
            # If no validation regions, use a single region covering the entire screen
            if not validation_regions:
                height, width = screenshot.shape[:2]
                validation_regions = [{"x1": 0, "y1": 0, "x2": width, "y2": height}]
            
            # Check validation regions
            region_scores = []
            for region in validation_regions:
                # Extract region coordinates
                x1, y1, x2, y2 = region['x1'], region['y1'], region['x2'], region['y2']
                
                # Compare region
                region_score = self.comparator.compare_region(
                    screenshot, 
                    ref_image_path, 
                    x1, y1, x2, y2
                )
                region_scores.append(region_score)
            
            # Use maximum error (worst matching region) as overall error
            match_score = max(region_scores) if region_scores else float("inf")
            matches = match_score <= self.match_threshold
            
            return matches, match_score, screenshot_data
            
        except Exception as e:
            self.logger.error(f"Error in verify_screen: {e}")
            return False, 0.0, b''
    
    def wait_for_screen(self, device_id: str, 
                       expected_screen_id: str,
                       ref_image_path: str,
                       validation_regions: List[Dict[str, int]],
                       timeout: Optional[float] = None,
                       check_interval: float = 0.5) -> Tuple[bool, bytes]:
        """
        Wait for specific screen to appear
        
        Args:
            device_id: Device identifier
            expected_screen_id: Expected screen ID
            ref_image_path: Path to reference image
            validation_regions: List of validation region dictionaries
            timeout: Timeout in seconds (None for default)
            check_interval: Time between checks in seconds
            
        Returns:
            Tuple of (success, final_screenshot)
        """
        if timeout is None:
            timeout = self.verification_timeout
            
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            # Check screen
            matches, _, screenshot = self.verify_screen(
                device_id, 
                expected_screen_id,
                ref_image_path,
                validation_regions
            )
            
            if matches:
                return True, screenshot
                
            # Wait before next check
            time.sleep(check_interval)
            
        # Timeout - get one last screenshot
        _, _, final_screenshot = self.verify_screen(
            device_id, 
            expected_screen_id,
            ref_image_path,
            validation_regions
        )
        
        return False, final_screenshot
