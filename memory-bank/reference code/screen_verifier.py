#!/usr/bin/env python3

import cv2
import numpy as np
from pathlib import Path
import json
import time
import subprocess
import logging
import pytesseract
from typing import Dict, Optional, Tuple
from PIL import Image

from device_controller import TikTokDeviceController
from connection_manager import ConnectionManager

class ScreenVerifier:
    """Screen verification using template matching"""
    
    def __init__(self, device_name: Optional[str] = None, models_path: Optional[Path] = None, debug: bool = False):
        # Set paths
        self.models_path = models_path or Path("reference_system")
        self.registry_path = self.models_path / "state_registry.json"
        self.debug = debug
        
        # Initialize device if provided
        if device_name:
            # Initialize managers
            self.connection_manager = ConnectionManager()
            self.device_id = self.connection_manager.get_device_id(device_name)
            self.device_controller = TikTokDeviceController(device_name)
            
            # Get device paths
            self.device_path = self.device_controller.get_device_path()
            self.debug_path = self.device_path / "debug"
            self.debug_path.mkdir(parents=True, exist_ok=True)
            
            # Configure logging
            log_path = self.debug_path / "screen_verifier.log"
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_path),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
        
        # Load registry and set threshold
        self.registry = self._load_registry()
        self.MATCH_THRESHOLD = 0.95

    def _load_registry(self) -> Dict:
        """Load state registry configuration"""
        try:
            with open(self.registry_path) as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load state registry: {e}")
            return {"states": {}}

    def compare_regions(self, current_img: np.ndarray, reference_img: np.ndarray, state: str, region: str) -> float:
        """Compare two image regions and save debug images"""
        try:
            # Extract region coordinates
            region_info = self.registry["states"][state]["regions"][region]
            x, y = region_info["coordinates"]
            w, h = region_info["dimensions"]
            
            # Extract regions from both images
            current_region = current_img[y:y+h, x:x+w]
            reference_region = reference_img[y:y+h, x:x+w]
            
            # Convert to grayscale
            current_gray = cv2.cvtColor(current_region, cv2.COLOR_BGR2GRAY)
            reference_gray = cv2.cvtColor(reference_region, cv2.COLOR_BGR2GRAY)
            
            # Compare regions using TM_SQDIFF_NORMED (0 means perfect match, 1 means completely different)
            score = 1.0 - cv2.matchTemplate(current_gray, reference_gray, cv2.TM_SQDIFF_NORMED).min()
            
            # Save debug images if debug mode is enabled
            if self.debug_path.exists():
                debug_folder = self.debug_path / state / region
                debug_folder.mkdir(parents=True, exist_ok=True)
                
                cv2.imwrite(str(debug_folder / "current.png"), current_region)
                cv2.imwrite(str(debug_folder / "reference.png"), reference_region)
                cv2.imwrite(str(debug_folder / "current_gray.png"), current_gray)
                cv2.imwrite(str(debug_folder / "reference_gray.png"), reference_gray)
                
                with open(debug_folder / "match_score.txt", "w") as f:
                    f.write(f"Match score: {score:.3f}")
            
            return score
        
        except Exception as e:
            self.logger.error(f"Region comparison failed: {str(e)}")
            return 0.0

    def _get_region_image(self, screen: np.ndarray, coords: Dict) -> np.ndarray:
        """Extract region from screenshot using coordinates"""
        try:
            x, y = coords["coordinates"]
            w, h = coords["dimensions"]
            return screen[y:y+h, x:x+w]
        except Exception as e:
            self.logger.error(f"Failed to extract region: {e}")
            return np.array([])

    def _get_reference_image(self, state: str, region: str) -> Optional[Path]:
        """Get most recent reference image for region with timestamp pattern"""
        try:
            # Get region info from registry to determine category
            state_config = self.registry["states"].get(state, {})
            region_info = state_config.get("regions", {}).get(region, {})
            category = region_info.get("category")
            
            if not category:
                self.logger.error(f"No category found for {state}/{region}")
                return None

            # Set path based on category
            if category == "element":
                state_path = self.models_path / "elements" / state
            else:  # regions and other categories
                state_path = self.models_path / "regions" / state
                
            if not state_path.exists():
                self.logger.error(f"State path does not exist: {state_path}")
                return None

            # Look for files matching pattern: Region_YYYYMMDD_HHMMSS.png
            matches = list(state_path.glob(f"{region.capitalize()}_[0-9]*_[0-9]*.png"))
            
            if not matches:
                self.logger.error(f"No reference images found for {state}/{region}")
                self.logger.info(f"Looked in: {state_path}")
                return None
                
            # Return most recent by timestamp in filename
            latest = max(matches, key=lambda p: p.stem.split('_')[-2:])
            self.logger.info(f"Selected reference image: {latest.name}")
            return latest
                
        except Exception as e:
            self.logger.error(f"Error finding reference image for {state}/{region}: {str(e)}")
            return None

    def _verify_text(self, region: np.ndarray, state: str, region_name: str) -> bool:
        """Verify text in region using OCR"""
        try:
            # Convert to grayscale for OCR
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            
            # Save debug image
            debug_folder = self.debug_path / state / region_name / "ocr"
            debug_folder.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(debug_folder / "ocr_input.png"), gray)
            
            # Perform OCR
            text = pytesseract.image_to_string(gray).strip()
            self.logger.info(f"OCR Text for {state}/{region_name}: '{text}'")
            
            # Save OCR result
            with open(debug_folder / "ocr_result.txt", "w") as f:
                f.write(text)
            
            return len(text) > 0
            
        except Exception as e:
            self.logger.error(f"OCR Error: {e}")
            return False

    def capture_screen(self) -> Optional[np.ndarray]:
        """Capture current screen as numpy array"""
        try:
            result = subprocess.run(
                [str(self.device_controller.adb_path), "-s", self.device_id, "exec-out", "screencap -p"],
                capture_output=True,
                check=True
            )
            
            screen_bytes = np.frombuffer(result.stdout, dtype=np.uint8)
            screen = cv2.imdecode(screen_bytes, cv2.IMREAD_COLOR)
            
            if screen is None:
                self.logger.error("Failed to decode screen image")
                return None
            
            # Save debug screenshot
            cv2.imwrite(str(self.debug_path / "current_screen.png"), screen)
            return screen
            
        except Exception as e:
            self.logger.error(f"Screen capture failed: {e}")
            return None

    def get_category(self, state: str) -> str:
        """Get category for a state"""
        if state in self.registry.get("states", {}):
            return "states"
        elif state in self.registry.get("interrupts", {}):
            return "interrupts"
        return ""

    def verify_state(self, screen_path: str, expected_state: Optional[str] = None) -> Tuple[bool, str, float]:
        """Verify if a screen matches an expected state or find best matching state"""
        # Load screen image
        screen_img = cv2.imread(str(screen_path))
        if screen_img is None:
            raise ValueError(f"Could not load image {screen_path}")
            
        # If expected state provided, only check that one
        if expected_state:
            if expected_state not in self.registry["states"]:
                raise ValueError(f"State {expected_state} not found in registry")
                
            state_data = self.registry["states"][expected_state]
            if not state_data.get("screenshots"):
                raise ValueError(f"No screenshots found for state {expected_state}")
                
            # Get latest screenshot
            latest_screenshot = state_data["screenshots"][-1]
            # All reference images live in reference_system/models/s21/
            reference_path = self.models_path / "models" / "s21" / latest_screenshot
            if not reference_path.is_absolute():
                reference_path = self.models_path / reference_path
            
            # Load reference image
            ref_img = cv2.imread(str(reference_path))
            if ref_img is None:
                raise ValueError(f"Could not load reference image {reference_path}")
            
            # Compare validation regions
            validation_regions = [
                name for name, data in state_data["regions"].items()
                if data.get("category") == "validation"
            ]
            
            if not validation_regions:
                raise ValueError(f"No validation regions found for state {expected_state}")
                
            # Calculate scores for all validation regions
            region_scores = {}
            for region_name in validation_regions:
                score = self.compare_regions(screen_img, ref_img, expected_state, region_name)
                region_scores[region_name] = score
                if self.debug:
                    print(f"  Region '{region_name}': score = {score:.3f}")
            
            # Use minimum score as the match score
            match_score = min(region_scores.values())
            return match_score >= self.MATCH_THRESHOLD, expected_state, match_score
            
        # Otherwise check all states
        best_match = ""
        best_score = 0.0
        best_category = ""
        
        # Check against all states and interrupts
        for category in ["states", "interrupts"]:
            if category not in self.registry:
                continue
                
            for state_name, state_data in self.registry[category].items():
                if not state_data.get("screenshots"):
                    continue
                    
                # Get latest screenshot
                latest_screenshot = state_data["screenshots"][-1]
                reference_path = self.models_path / "models" / "s21" / latest_screenshot
                
                # Load reference image
                ref_img = cv2.imread(str(reference_path))
                if ref_img is None:
                    raise ValueError(f"Could not load reference image {reference_path}")
                
                # Compare validation regions
                validation_regions = [
                    name for name, data in state_data["regions"].items()
                    if data.get("category") == "validation"
                ]
                
                if not validation_regions:
                    if self.debug:
                        print(f"Warning: No validation regions found for {category[:-1]} '{state_name}'")
                    continue
                
                # Calculate scores for all validation regions
                region_scores = {}
                for region_name in validation_regions:
                    score = self.compare_regions(screen_img, ref_img, state_name, region_name)
                    region_scores[region_name] = score
                    if self.debug:
                        print(f"  Region '{region_name}': score = {score:.3f}")
                
                # Use minimum score as the match score
                match_score = min(region_scores.values())
                if self.debug:
                    print(f"Comparing with {category[:-1]} '{state_name}': score = {match_score:.3f} (min of {len(validation_regions)} regions)")
                
                if match_score > best_score:
                    best_score = match_score
                    best_match = state_name
                    best_category = category
        
        return best_score >= self.MATCH_THRESHOLD, best_match, best_score

    def verify_media_selector(self) -> bool:
        """Verify media selector screen specifically"""
        return self.verify_state("media_selector_verification")

    def verify_upload_screen(self) -> bool:
        """Verify upload screen specifically"""
        return self.verify_state("upload_screen")
