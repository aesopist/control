from pathlib import Path
import subprocess
import re
import time
import json
from typing import Dict, Tuple, Optional
from connection_manager import ConnectionManager
from utils.app_registry import AppRegistry

class APKVersionManager:
    def __init__(self):
        self.base_path = Path(__file__).parent.resolve()
        self.apk_folder = self.base_path / "apk_files"
        self.adb_path = self.base_path / "platform-tools" / "adb.exe"
        self.aapt_path = self.base_path / "platform-tools" / "aapt2.exe"
        # Use the singleton instance of ConnectionManager
        self.connection_manager = ConnectionManager.get_instance()
        # Initialize AppRegistry
        self.app_registry = AppRegistry.get_instance()

    def get_apk_version(self, apk_path: Path) -> Tuple[str, str]:
        """Get package name and version from APK file using aapt"""
        try:
            # First try aapt if available
            if self.aapt_path.exists():
                result = subprocess.run(
                    [str(self.aapt_path), "dump", "badging", str(apk_path)],
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
            else:
                # Fallback to bundled platform tools
                result = subprocess.run(
                    [str(self.adb_path), "shell", "pm", "dump", str(apk_path)],
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
            
            # Extract package name
            package_match = re.search(r"package: name='([^']+)'", result.stdout)
            if not package_match:
                # Try alternate format
                package_match = re.search(r"packageName='([^']+)'", result.stdout)
                if not package_match:
                    print(f"Package name not found in output: {result.stdout[:200]}...")  # Debug output
                    raise ValueError("Could not find package name")
            package_name = package_match.group(1)
            
            # Extract version name
            version_match = re.search(r"versionName='([^']+)'", result.stdout)
            if not version_match:
                print(f"Version not found in output: {result.stdout[:200]}...")  # Debug output
                raise ValueError("Could not find version info")
            version_name = version_match.group(1)
            
            print(f"Successfully parsed APK: {package_name} version {version_name}")  # Debug output
            return package_name, version_name
            
        except subprocess.CalledProcessError as e:
            print(f"Process error reading APK {apk_path.name}: {str(e)}")
            print(f"Command output: {e.output}")  # Debug output
            return None, None
        except Exception as e:
            print(f"Error reading APK {apk_path.name}: {str(e)}")
            return None, None

    def get_installed_version(self, device_id: str, package_name: str) -> Optional[str]:
        """Get installed version of app on device"""
        try:
            result = subprocess.run(
                [str(self.adb_path), "-s", device_id, "shell", "dumpsys", "package", package_name],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            # Extract version name
            version_match = re.search(r"versionName=([^\s]+)", result.stdout)
            if version_match:
                return version_match.group(1)
                
            # Try alternate format
            version_match = re.search(r"version=([^\s]+)", result.stdout)
            if version_match:
                return version_match.group(1)
                
            return None
            
        except Exception as e:
            print(f"Error checking device {device_id}: {str(e)}")
            return None

    def install_apk(self, device_id: str, apk_path: Path) -> bool:
        """Install or update APK on device, handling split APKs"""
        try:
            # Get the directory containing the APK
            apk_dir = apk_path.parent
            
            # Check if this is a split APK installation
            install_info_path = apk_dir / 'install_info.json'
            if install_info_path.exists():
                print("Found split APK installation info...")
                with open(install_info_path) as f:
                    install_info = json.load(f)
                
                # Collect all APK paths
                apk_files = []
                for split_name in install_info['split_apks']:
                    split_path = apk_dir / split_name
                    if not split_path.exists():
                        print(f"Error: Missing split APK: {split_name}")
                        return False
                    apk_files.append(split_path)
                
                # Install all APKs together
                print(f"Installing {len(apk_files)} split APKs:")
                for apk in apk_files:
                    print(f"  - {apk.name}")
                    
                cmd = [str(self.adb_path), "-s", device_id, "install-multiple", "-r", "-g", "--no-streaming"]
                cmd.extend(str(p.absolute()) for p in apk_files)
                
                print(f"\nRunning command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            else:
                # Regular single APK installation
                print(f"Installing {apk_path.name}...")
                result = subprocess.run([
                    str(self.adb_path),
                    "-s", device_id,
                    "install", "-r", "-g",  # -r flag for replacing existing app, -g to grant permissions
                    str(apk_path.absolute())
                ], capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                print(f"Installation failed!")
                print(f"Command output: {result.stdout}")
                print(f"Error output: {result.stderr}")
                return False
            
            print("Installation completed successfully")    
            return True
            
        except Exception as e:
            print(f"Installation error: {str(e)}")
            return False

    def get_available_devices(self) -> Dict[str, str]:
        """
        Get dictionary of friendly_name -> device_id for connected devices
        Uses the ConnectionManager to get devices properly
        """
        devices = {}
        
        # Get all devices from ConnectionManager
        available_devices = self.connection_manager.get_available_devices()
        
        # Extract friendly_name -> device_id mapping
        for friendly_name, device_info in available_devices.items():
            device_id = device_info.get("device_id")
            if device_id:
                devices[friendly_name] = device_id
                
        return devices

    def find_apk_files(self) -> Dict[str, Dict]:
        """Find all APK files in base dir and apk_files subfolder"""
        apks = {}
        
        # Create apk_files directory if it doesn't exist
        self.apk_folder.mkdir(exist_ok=True)
        
        # Search paths
        search_paths = [self.base_path, self.apk_folder]
        
        for search_path in search_paths:
            print(f"\nSearching in: {search_path}")  # Debug output
            
            # First look for install_info.json files (indicating split APKs)
            for install_info_path in search_path.rglob('install_info.json'):
                try:
                    with open(install_info_path) as f:
                        install_info = json.load(f)
                        
                    # Get the base APK path
                    base_apk = install_info_path.parent / install_info['split_apks'][0]
                    if base_apk.exists():
                        print(f"Found split APK package: {base_apk.name}")
                        package_name, version = self.get_apk_version(base_apk)
                        if package_name and version:
                            apks[package_name] = {
                                'path': base_apk,
                                'version': version,
                                'is_split': True
                            }
                except Exception as e:
                    print(f"Error processing split APK info: {str(e)}")
            
            # Then look for regular APKs
            for apk_path in search_path.glob("*.apk"):
                # Skip if parent directory already processed as split APK
                if any(info.get('is_split', False) and info['path'].parent == apk_path.parent 
                      for info in apks.values()):
                    continue
                    
                print(f"Found APK: {apk_path.name}")
                package_name, version = self.get_apk_version(apk_path)
                if package_name and version:
                    apks[package_name] = {
                        'path': apk_path,
                        'version': version,
                        'is_split': False
                    }
        return apks

    def process_device(self, device_name: str, device_id: str, apks: Dict[str, Dict]) -> Dict[str, str]:
        """Process a single device, handling installs/updates as needed"""
        results = {}
        
        # Get installed packages
        print(f"  Checking installed packages...")
        installed_packages = self.get_installed_packages(device_id)
        
        if not installed_packages:
            print(f"  Error: Failed to get installed packages")
            return results
            
        # Process each APK
        for package_name, info in apks.items():
            print(f"\n  Processing {info['path'].name}...")
            
            # Check if package is in registry
            app_name = self.app_registry.get_app_name_by_package(package_name)
            if not app_name:
                # Generate app name from package name
                app_name = package_name.split('.')[-1].lower()
                if app_name == 'android':
                    # Handle special case for android packages
                    parts = package_name.split('.')
                    if len(parts) > 2:
                        app_name = parts[-2].lower()
                
                # Add to registry
                description = f"Auto-detected from APK: {info['path'].name}"
                success = self.app_registry.add_or_update_app(app_name, package_name, description)
                
                if success:
                    print(f"    + Added {app_name} ({package_name}) to registry")
                else:
                    print(f"    ! Failed to add {app_name} to registry")
            else:
                print(f"    - Found in registry as: {app_name}")
            
            # Check if already installed
            installed_version = installed_packages.get(package_name)
            
            if installed_version:
                print(f"    - Already installed (version: {installed_version})")
                
                # Check if versions match
                if installed_version == info['version']:
                    results[package_name] = "Already up to date"
                else:
                    print(f"    - Updating from {installed_version} to {info['version']}...")
                    
                    # Install the APK
                    success = self.install_apk(device_id, info['path'])
                    
                    if success:
                        results[package_name] = f"Updated ({installed_version} → {info['version']})"
                    else:
                        results[package_name] = f"Update failed"
            else:
                print(f"    - Not installed, installing version {info['version']}...")
                
                # Install the APK
                success = self.install_apk(device_id, info['path'])
                
                if success:
                    results[package_name] = f"Installed (version: {info['version']})"
                else:
                    results[package_name] = "Installation failed"
                    
        return results

    def get_installed_packages(self, device_id: str) -> Dict[str, str]:
        """Get installed packages on a device"""
        try:
            result = subprocess.run(
                [str(self.adb_path), "-s", device_id, "shell", "pm", "list", "packages"],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            # Extract package names
            package_names = re.findall(r"package:([^\s]+)", result.stdout)
            
            # Get versions for each package
            installed_packages = {}
            for package_name in package_names:
                version = self.get_installed_version(device_id, package_name)
                if version:
                    installed_packages[package_name] = version
                    
            return installed_packages
            
        except Exception as e:
            print(f"Error checking device {device_id}: {str(e)}")
            return {}

def main():
    # Initialize APKVersionManager (which will init ConnectionManager)
    manager = APKVersionManager()
    
    print("\nAPK Version Manager")
    print("==================")
    
    # Find APK files
    print("\nScanning for APK files...")
    apks = manager.find_apk_files()
    
    if not apks:
        print("No APK files found in base directory or apk_files folder!")
        return
        
    print(f"\nFound {len(apks)} APK file(s):")
    for package_name, info in apks.items():
        print(f"• {info['path'].name}")
        print(f"  - Package: {package_name}")
        print(f"  - Version: {info['version']}")
    
    # Check APKs against app registry and update if needed
    print("\nChecking APKs against app registry...")
    app_registry = AppRegistry.get_instance()
    registry_updated = False
    
    for package_name, info in apks.items():
        # Check if package is already in registry
        app_name = app_registry.get_app_name_by_package(package_name)
        
        if not app_name:
            # Generate app name from package name
            app_name = package_name.split('.')[-1].lower()
            if app_name == 'android':
                # Handle special case for android packages
                parts = package_name.split('.')
                if len(parts) > 2:
                    app_name = parts[-2].lower()
            
            # Add to registry
            description = f"Detected from APK: {info['path'].name}"
            success = app_registry.add_or_update_app(app_name, package_name, description)
            
            if success:
                print(f"  + Added {app_name} ({package_name}) to registry")
                registry_updated = True
            else:
                print(f"  ! Failed to add {app_name} to registry")
    
    if registry_updated:
        print("\nApp registry has been updated with new APKs")
    else:
        print("\nNo changes needed to app registry")
    
    # Add required delay for ConnectionManager to initialize
    print("\nInitializing device manager...")
    time.sleep(3)  # IMPORTANT: 3-second delay for ConnectionManager initialization
    
    # Get connected devices
    print("\nChecking connected devices...")
    devices = manager.get_available_devices()
    
    if not devices:
        print("No devices connected!")
        return
        
    # Process each device
    print("\nProcessing Devices:")
    print("==================")
    
    all_results = {}
    for device_name, device_id in devices.items():
        print(f"\n{device_name} ({device_id}):")
        results = manager.process_device(device_name, device_id, apks)
        all_results[device_name] = results
    
    # Show summary
    print("\nOperation Summary:")
    print("=================")
    for device_name, results in all_results.items():
        print(f"\n{device_name}:")
        for package_name, status in results.items():
            print(f"• {package_name}: {status}")

if __name__ == "__main__":
    main()
