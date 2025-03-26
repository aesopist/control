"""
Screen verification for Control component.
Handles verifying device screens against reference images in workflow packages.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import threading

import cv2
import numpy as np

from ..config import Config
from ..device_manager import DeviceManager
from .comparator import ImageComparator
from .registry import ScreenRegistry

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
        
        # Initialize components
        self.comparator = ImageComparator()
        self.registry = ScreenRegistry()
        
        # Screenshot cache
        self._screenshot_cache = {}  # device_id -> {'timestamp': time, 'image': bytes}
        self._cache_lock = threading.Lock()
        
        # Default settings
        self.match_threshold = 0.95  # Minimum match score for validation regions
        self.verification_timeout = self.config.get('workflow.verification_timeout', 10)
        
        self._initialized = True
    
    def verify_screen(self, device_id: str, 
                      workflow_id: str, 
                      expected_screen_id: Optional[str] = None,
                      use_cache: bool = True) -> Tuple[bool, str, float, bytes]:
        """
        Verify current device screen against expected screen or find best match.
        
        Args:
            device_id: Device identifier
            workflow_id: Workflow ID to get screen registry from
            expected_screen_id: Expected screen ID or None to find best match
            use_cache: Whether to use cached screenshot if available
            
        Returns:
            Tuple of (matches, screen_id, match_score, screenshot_data)
        """
        try:
            # Get screenshot
            if use_cache:
                screenshot_data = self._get_cached_screenshot(device_id)
            
            if not use_cache or screenshot_data is None:
                screenshot_data = self.device_manager.capture_screenshot(device_id)
                self._update_screenshot_cache(device_id, screenshot_data)
            
            if screenshot_data is None:
                self.logger.error(f"Failed to capture screenshot for {device_id}")
                return False, "", 0.0, b''
            
            # Get screen registry for workflow
            registry = self.registry.get_registry(workflow_id)
            if not registry:
                self.logger.error(f"No screen registry found for workflow {workflow_id}")
                return False, "", 0.0, screenshot_data
            
            # Convert screenshot to numpy array
            np_array = np.frombuffer(screenshot_data, dtype=np.uint8)
            screenshot = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
            
            if screenshot is None:
                self.logger.error(f"Failed to decode screenshot for {device_id}")
                return False, "", 0.0, screenshot_data
            
            # If expected screen provided, only check that
            if expected_screen_id:
                return self._check_specific_screen(screenshot, expected_screen_id, 
                                                  registry, screenshot_data)
            
            # Otherwise find best match among all screens
            return self._find_best_match(screenshot, registry, screenshot_data)
            
        except Exception as e:
            self.logger.error(f"Error in verify_screen: {e}")
            return False, "", 0.0, screenshot_data if screenshot_data else b''
    
    def _check_specific_screen(self, screenshot: np.ndarray, 
                              screen_id: str, 
                              registry: Dict, 
                              screenshot_data: bytes) -> Tuple[bool, str, float, bytes]:
        """Check if screenshot matches a specific screen"""
        if screen_id not in registry:
            self.logger.error(f"Screen ID {screen_id} not found in registry")
            return False, "", 0.0, screenshot_data
        
        screen_info = registry[screen_id]
        
        # Get reference image path
        ref_image_path = screen_info.get('image')
        if not ref_image_path:
            self.logger.error(f"No reference image for screen {screen_id}")
            return False, "", 0.0, screenshot_data
        
        # Get validation regions
        validation_regions = screen_info.get('validation_regions', [])
        if not validation_regions:
            self.logger.error(f"No validation regions for screen {screen_id}")
            return False, "", 0.0, screenshot_data
        
        # Compare regions
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
        
        # Use minimum score as overall match
        match_score = min(region_scores) if region_scores else 0.0
        matches = match_score >= self.match_threshold
        
        return matches, screen_id, match_score, screenshot_data
    
    def _find_best_match(self, screenshot: np.ndarray, 
                        registry: Dict, 
                        screenshot_data: bytes) -> Tuple[bool, str, float, bytes]:
        """Find best matching screen for screenshot"""
        best_match = ""
        best_score = 0.0
        
        # Check all screens in registry
        for screen_id, screen_info in registry.items():
            # Skip screens without reference images or validation regions
            ref_image_path = screen_info.get('image')
            validation_regions = screen_info.get('validation_regions', [])
            
            if not ref_image_path or not validation_regions:
                continue
            
            # Compare regions
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
            
            # Use minimum score as overall match for this screen
            match_score = min(region_scores) if region_scores else 0.0
            
            # Keep track of best match
            if match_score > best_score:
                best_score = match_score
                best_match = screen_id
        
        matches = best_score >= self.match_threshold
        return matches, best_match, best_score, screenshot_data
    
    def _get_cached_screenshot(self, device_id: str) -> Optional[bytes]:
        """Get cached screenshot if available and not too old"""
        with self._cache_lock:
            cache_entry = self._screenshot_cache.get(device_id)
            if cache_entry:
                # Check if cache is fresh (less than 1 second old)
                age = time.time() - cache_entry['timestamp']
                if age <= 1.0:  # 1 second max age
                    return cache_entry['image']
        return None
    
    def _update_screenshot_cache(self, device_id: str, screenshot_data: bytes):
        """Update screenshot cache"""
        with self._cache_lock:
            self._screenshot_cache[device_id] = {
                'timestamp': time.time(),
                'image': screenshot_data
            }
    
    def wait_for_screen(self, device_id: str, 
                       workflow_id: str,
                       expected_screen_id: str,
                       timeout: Optional[float] = None,
                       check_interval: float = 0.5) -> Tuple[bool, bytes]:
        """
        Wait for specific screen to appear
        
        Args:
            device_id: Device identifier
            workflow_id: Workflow ID
            expected_screen_id: Expected screen ID
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
            matches, screen_id, score, screenshot = self.verify_screen(
                device_id, 
                workflow_id,
                expected_screen_id,
                use_cache=False  # Always get fresh screenshot when waiting
            )
            
            if matches:
                return True, screenshot
                
            # Wait before next check
            time.sleep(check_interval)
            
        # Timeout - get one last screenshot
        _, _, _, final_screenshot = self.verify_screen(
            device_id, 
            workflow_id,
            expected_screen_id,
            use_cache=False
        )
        
        return False, final_screenshot