"""
Image comparison for Control component.
Handles comparing regions of images for screen verification.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Tuple, Optional, Union

import cv2
import numpy as np

from ..config import Config

class ImageComparator:
    """
    Handles image comparison for screen verification.
    """
    
    def __init__(self):
        # Get configuration
        self.config = Config()
        
        # Initialize paths
        self.base_path = Path(__file__).parent.parent.parent
        self.temp_path = self.base_path / "temp" / "debug"
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        self.logger = logging.getLogger("ImageComparator")
        
        # Reference image cache
        self._ref_image_cache = {}  # path -> image
        
        # Debug mode
        self.debug_mode = self.config.get('debug.screen_verification', False)
    
    def compare_region(self, 
                      current_img: np.ndarray, 
                      ref_path: Union[str, Path], 
                      x1: int, y1: int, 
                      x2: int, y2: int) -> float:
        """
        Compare region of current image with same region in reference image
        
        Args:
            current_img: Current screenshot as numpy array
            ref_path: Path to reference image (string or Path)
            x1, y1: Top-left coordinates of region
            x2, y2: Bottom-right coordinates of region
            
        Returns:
            Match score (0.0 to 1.0)
        """
        try:
            # Get reference image
            ref_img = self._get_reference_image(ref_path)
            if ref_img is None:
                self.logger.error(f"Failed to load reference image: {ref_path}")
                return 0.0
            
            # Check if images have same dimensions
            if current_img.shape != ref_img.shape:
                self.logger.warning(
                    f"Image dimensions don't match: {current_img.shape} vs {ref_img.shape}"
                )
                # Resize reference to match current if needed
                if ref_img.shape[0] != current_img.shape[0] or ref_img.shape[1] != current_img.shape[1]:
                    ref_img = cv2.resize(ref_img, (current_img.shape[1], current_img.shape[0]))
            
            # Ensure region is within bounds
            height, width = current_img.shape[:2]
            x1 = max(0, min(x1, width - 1))
            y1 = max(0, min(y1, height - 1))
            x2 = max(x1 + 1, min(x2, width))
            y2 = max(y1 + 1, min(y2, height))
            
            # Debug: print image dimensions and region extraction coordinates
            print(f"[DEBUG] Reference path: {ref_path}")
            print(f"[DEBUG] Current image shape: {current_img.shape}, reference image shape: {ref_img.shape}")
            print(f"[DEBUG] Extracting region with coordinates: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
            
            # Extract regions
            current_region = current_img[y1:y2, x1:x2]
            ref_region = ref_img[y1:y2, x1:x2]
            
            # Debug: print extracted region shapes
            print(f"[DEBUG] Extracted current_region shape: {current_region.shape}, ref_region shape: {ref_region.shape}")
            
            # Convert to grayscale for comparison
            current_gray = cv2.cvtColor(current_region, cv2.COLOR_BGR2GRAY)
            ref_gray = cv2.cvtColor(ref_region, cv2.COLOR_BGR2GRAY)
            
            # Compute Mean Squared Error (MSE) between the regions
            mse = float(np.mean((current_gray.astype("float32") - ref_gray.astype("float32")) ** 2))
            print(f"[DEBUG] Computed MSE for region: {mse}")
            match_score = mse
            
            # Debug output if enabled
            if self.debug_mode:
                self._save_debug_images(current_region, ref_region, match_score)
            
            return match_score
            
        except Exception as e:
            self.logger.error(f"Error comparing regions: {e}")
            return 0.0
    
    def _get_reference_image(self, ref_path: Union[str, Path]) -> Optional[np.ndarray]:
        """
        Get reference image, using cache if available
        
        Args:
            ref_path: Path to reference image
            
        Returns:
            Reference image as numpy array or None if loading fails
        """
        # Convert to Path if string
        if isinstance(ref_path, str):
            ref_path = Path(ref_path)
            
        # Convert to absolute path if not already
        if not ref_path.is_absolute():
            ref_path = self.base_path / ref_path
        
        # Check cache
        cache_key = str(ref_path)
        if cache_key in self._ref_image_cache:
            return self._ref_image_cache[cache_key]
        
        # Load image
        try:
            image = cv2.imread(str(ref_path))
            if image is not None:
                # Cache image
                self._ref_image_cache[cache_key] = image
            return image
        except Exception as e:
            self.logger.error(f"Error loading reference image {ref_path}: {e}")
            return None
    
    def _save_debug_images(self, current_region: np.ndarray, 
                          ref_region: np.ndarray, 
                          match_score: float):
        """
        Save debug images for visualization
        
        Args:
            current_region: Current region image
            ref_region: Reference region image
            match_score: Match score
        """
        try:
            # Create debug directory
            debug_dir = self.temp_path / f"debug_{int(time.time())}"
            debug_dir.mkdir(exist_ok=True)
            
            # Save images
            cv2.imwrite(str(debug_dir / "current_region.png"), current_region)
            cv2.imwrite(str(debug_dir / "ref_region.png"), ref_region)
            
            # Save match score
            with open(debug_dir / "match_score.txt", "w") as f:
                f.write(f"Match score: {match_score:.4f}")
        except Exception as e:
            self.logger.error(f"Error saving debug images: {e}")
