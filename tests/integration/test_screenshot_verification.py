import subprocess
import time
from pathlib import Path
from PIL import Image

# Device ID for phone1 as per the known mapping:
DEVICE_ID = "192.168.1.201:5555"

def test_capture_screenshot_flat():
    """
    Capture a screenshot from phone1 using a flat ADB command and verify it can be opened as an image.
    This test uses a simple shell redirection method to directly write the screenshot output into a PNG file.
    """
    base_dir = Path("tests/data/screenshots")
    base_dir.mkdir(parents=True, exist_ok=True)
    flat_path = base_dir / "flat_screenshot.png"
    
    adb_executable = Path("platform-tools/adb.exe")
    # Construct the command using shell redirection
    command = f'"{adb_executable}" -s {DEVICE_ID} exec-out screencap -p > "{flat_path}"'
    subprocess.run(command, shell=True, check=True, timeout=10)
    time.sleep(2)  # Wait for file write to complete

    try:
        img = Image.open(flat_path)
        width, height = img.size
    except Exception as e:
        raise Exception("Unable to open the flat screenshot: " + str(e))
    
    assert width > 0 and height > 0, "Captured screenshot has invalid dimensions"
    print(f"Flat screenshot captured successfully: {flat_path.resolve()}")

if __name__ == "__main__":
    test_capture_screenshot_flat()
    print("Test completed. Please manually verify the screenshot file.")
