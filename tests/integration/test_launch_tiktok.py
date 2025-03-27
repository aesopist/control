import subprocess
import time
from pathlib import Path

# Device ID for phone1 as per the known mapping:
DEVICE_ID = "192.168.1.201:5555"
# TikTok component from the registry (package and splash activity):
COMPONENT = "com.zhiliaoapp.musically/com.ss.android.ugc.aweme.splash.SplashActivity"

def test_launch_tiktok():
    """
    Test launching TikTok on phone1 using an ADB command.
    This simulates a live command sent via a JSON reference.
    The test executes the command and asserts that it completes successfully.
    """
    adb_executable = Path("platform-tools/adb.exe")
    # Construct the command using the full component string:
    command = [
        str(adb_executable),
        "-s", DEVICE_ID,
        "shell",
        "am", "start",
        "-n", COMPONENT
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    
    # Log outputs for debugging:
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    
    # Assert that the command executed successfully.
    assert result.returncode == 0, f"Failed to launch TikTok: {result.stderr}"
    
    # Optional: Wait a few seconds to allow the app to launch.
    time.sleep(5)
    
    print("TikTok launched successfully on device", DEVICE_ID)

if __name__ == "__main__":
    test_launch_tiktok()
    print("Test completed. Verify the TikTok app opened on your device.")
