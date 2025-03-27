import subprocess
import time
from pathlib import Path
import cv2
import numpy as np

# Device ID for phone1 as per the known mapping:
DEVICE_ID = "192.168.1.201:5555"

def test_screen_verifier():
    """
    This test verifies the screen verifier functionality using our MSE-based verifier.
    """
    from control.verification.comparator import ImageComparator
    
    base_dir = Path("tests/data/screenshots")
    base_dir.mkdir(parents=True, exist_ok=True)

    # Path to the reference screenshot
    reference_path = base_dir / "flat_screenshot.png"
    print(f"[TEST] Reference path: {reference_path.absolute()}")
    print(f"[TEST] Reference file exists: {reference_path.exists()}")
    
    # Path to the TikTok screenshot
    tiktok_screenshot = base_dir / "tiktok_screenshot.png"
    print(f"[TEST] TikTok screenshot path: {tiktok_screenshot.absolute()}")
    print(f"[TEST] TikTok screenshot exists: {tiktok_screenshot.exists()}")
    
    # Create an ImageComparator
    comparator = ImageComparator()
    
    # Load the images
    ref_img = cv2.imread(str(reference_path))
    tiktok_img = cv2.imread(str(tiktok_screenshot))
    
    if ref_img is None or tiktok_img is None:
        raise ValueError("Failed to load one or both images")
    
    print(f"[TEST] Reference image shape: {ref_img.shape}")
    print(f"[TEST] TikTok image shape: {tiktok_img.shape}")
    
    # Define a validation region (middle of the screen)
    x1, y1, x2, y2 = 300, 300, 500, 500
    
    # Compare the region in both images
    mse = comparator.compare_region(ref_img, tiktok_screenshot, x1, y1, x2, y2)
    print(f"[TEST] Computed MSE between reference and TikTok: {mse}")
    
    # The MSE should be above our threshold (1000) if the images are different
    assert mse > 1000, "The images should be different but MSE is too low"
    print(f"[TEST] Verification passed: MSE ({mse}) is above threshold (1000)")


#########################################
# New tests using the real verifier
#########################################

def test_defined_region_verifier_pass():
    """
    Test ScreenVerifier with defined validation region using the current screen as reference.
    The test captures a reference screenshot from the open TikTok screen and then verifies that,
    using the defined region (x:300-500, y:300-500), the verifier passes.
    """
    from control.verification.verifier import ScreenVerifier
    verifier = ScreenVerifier()
    expected_screen = "tiktok"
    # Define validation region: region in the middle of the screen
    validation_regions = [{"x1": 300, "y1": 300, "x2": 500, "y2": 500}]
    # Path for reference screenshot
    ref_path = Path("tests/data/screenshots/tiktok_reference.png")
    
    # Capture and save the reference screenshot from the currently open TikTok screen.
    screenshot_data = verifier.device_manager.capture_screenshot(DEVICE_ID)
    np_array = np.frombuffer(screenshot_data, dtype=np.uint8)
    screenshot = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    cv2.imwrite(str(ref_path), screenshot)
    
    # Use the verifier to compare the current screen against the reference (should pass)
    matches, score, _ = verifier.verify_screen(DEVICE_ID, expected_screen, str(ref_path), validation_regions)
    assert matches, f"Expected screen to match (pass) but got score {score}"
    print(f"Defined region verifier pass test succeeded with score {score:.4f}.")

def test_defined_region_verifier_fail():
    """
    Test ScreenVerifier by modifying the reference image in the defined validation region.
    The test alters the reference screenshot (filling the region with black) and then verifies that
    the verifier detects a mismatch.
    """
    from control.verification.verifier import ScreenVerifier
    verifier = ScreenVerifier()
    expected_screen = "tiktok"
    validation_regions = [{"x1": 300, "y1": 300, "x2": 500, "y2": 500}]
    ref_path = Path("tests/data/screenshots/tiktok_reference.png")
    modified_ref_path = Path("tests/data/screenshots/tiktok_reference_modified.png")
    
    # Read the reference image
    ref_img = cv2.imread(str(ref_path))
    if ref_img is None:
        raise ValueError("Reference image not found. Run test_defined_region_verifier_pass first.")
    
    # Alter the defined validation region: fill region with black (simulate mismatch)
    ref_img[300:500,300:500] = 0
    cv2.imwrite(str(modified_ref_path), ref_img)
    
    # Verify using the modified reference image; should fail due to mismatch
    matches, score, _ = verifier.verify_screen(DEVICE_ID, expected_screen, str(modified_ref_path), validation_regions)
    assert not matches, f"Expected screen to fail verification but got score {score}"
    print(f"Defined region verifier fail test succeeded with score {score:.4f} (mismatch detected).")

if __name__ == "__main__":
    test_screen_verifier()
    test_defined_region_verifier_pass()
    test_defined_region_verifier_fail()
    print("All screen verifier tests completed successfully.")
