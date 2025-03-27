# Test Learnings and System Requirements

**Overview:**  
This document captures critical learnings and recommendations from our integration tests and system experiments. It serves as a reference for any changes that impact other systems, particularly the workflow JSON structure and how we perform app launches and screenshot captures. This document MUST be updated whenever a major learning or change occurs that impacts the design or operation of the overall system.

---

## Key Learnings

### 1. App Launch via ADB
- **Requirement:** When sending an "open" command in a workflow JSON, the command must include the main activity (entry point) for the app.  
- **Reason:** Generic intent invocations (using only package name plus standard MAIN/LAUNCHER intent flags) may fail or resolve ambiguously. Our tests have confirmed that launching apps reliably requires a fully qualified component string.
- **Recommendation:** Update workflow JSON commands to have a field for the app’s main or splash activity, e.g.:
  ```json
  "tiktok": {
      "package_name": "com.zhiliaoapp.musically",
      "component": "com.ss.android.ugc.aweme.splash.SplashActivity"
  }
  ```
  This ensures the system uses:
  ```
  adb -s <device_id> shell am start -n com.zhiliaoapp.musically/com.ss.android.ugc.aweme.splash.SplashActivity
  ```

### 2. Screenshot Capture Methodology
- **Observation:** The default ADB screenshot command can produce extraneous carriage return characters when using certain command options.
- **Solution:** Using the "adb exec-out screencap -p" command with shell redirection produces a flat PNG file that correctly formats the image data.
- **Recommendation:** All tests and automation should adopt the flat screenshot method:
  ```
  adb -s <device_id> exec-out screencap -p > <output_file>.png
  ```
  This ensures the PNG file is valid and can be processed reliably.

---

## Impact on Other Systems
- **Workflow JSON:**  
  The workflow JSON must now include the main activity (component) for any "open" commands. Without this, the ADB command might not target the correct entry point, leading to failures in app launch.
  
- **Testing and Monitoring:**  
  Our integration tests now validate:
    - That apps launch using the specific component.
    - That screenshots captured using the flat command are valid PNG files.
    
These requirements ensure consistency and reliability across automated test suites and live system commands.

---

**Maintenance:**  
Any major updates to how apps are launched or screenshots are captured (or any other changes that affect system operations) must be documented here immediately. This document should be reviewed regularly to ensure all teams are aligned with the current system requirements.
