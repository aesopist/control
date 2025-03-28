# Reference Code Documentation

This document contains reference code from version 7 that would possibly be useful to know in the Control function of Version 8, organized by filename.

## Table of Contents

1. [apk.py](#apkpy)
2. [app_registry.json](#app_registryjson)
3. [clipboard_utils.py](#clipboard_utilspy)
4. [connection_discord_bot_singleton.py](#connection_discord_bot_singletonpy)
5. [connection_manager.py](#connection_managerpy)
6. [connection_monitor_updated.py](#connection_monitor_updatedpy)
7. [core_device_ops.py](#core_device_opspy)
8. [device_config.json](#device_configjson)
9. [explorer_7.py](#explorer_7py)
10. [player_7.py](#player_7py)
11. [screen_verifier.py](#screen_verifierpy)
12. [swipe.py](#swipepy)
13. [tap.py](#tappy)
14. [test_special.py](#test_specialpy)
15. [type.py](#typepy)
16. [keyboard_client.py](#keyboard_clientpy)

## apk.py

```python
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

```

## app_registry.json

```json
{
  "tiktok": {
    "package_name": "com.zhiliaoapp.musically",
    "description": "TikTok social media app"
  },
  "instagram": {
    "package_name": "com.instagram.android",
    "description": "Instagram social media app"
  },
  "youtube": {
    "package_name": "com.google.android.youtube",
    "description": "YouTube video platform"
  },
  "youtube_studio": {
    "package_name": "com.google.android.apps.youtube.creator",
    "description": "YouTube Studio for content creators"
  },
  "gmail": {
    "package_name": "com.google.android.gm",
    "description": "Gmail email client"
  },
  "phone": {
    "package_name": "com.android.dialer",
    "description": "Phone dialer app"
  },
  "photo_gallery": {
    "package_name": "com.sec.android.gallery3d",
    "description": "Samsung photo gallery"
  },
  "settings": {
    "package_name": "com.android.settings",
    "description": "Android settings app"
  },
  "facebook": {
    "package_name": "com.facebook.katana",
    "description": "Detected from APK: Facebook_503.0.0.69.76_APKPure.apk (renamed from katana)"
  },
  "notepad": {
    "package_name": "com.atomczak.notepat",
    "description": "Detected from APK: Notepad - simple notes_1.37.0_APKPure.apk (renamed from notepat)"
  },
  "keyboard": {
    "package_name": "com.sociallama.keyboard",
    "description": "Detected from APK: app-debug.apk"
  }
}
```

## clipboard_utils.py

```python
#!/usr/bin/env python3
"""
Utility functions for clipboard operations using the SociaLlama Keyboard.
This module provides a clean interface for getting and setting clipboard content
by handling the special sequences that open the keyboard app.
"""

import os
import sys
import subprocess
from pathlib import Path

# Ensure base path is in sys.path for imports
base_path = Path(__file__).parent.parent
if str(base_path) not in sys.path:
    sys.path.append(str(base_path))

from utils.app_utils import get_current_app
from utils.device_id_converter import get_adb_device_id

def get_clipboard(device_id):
    """
    Get clipboard content from a device.
    
    Args:
        device_id: Device ID in any format (phoneX, IP:PORT, serial)
        
    Returns:
        Clipboard content as string
    """
    # Convert to ADB device ID format
    adb_device_id = get_adb_device_id(device_id)
    
    # Get the current app to return to
    current_app = get_current_app(adb_device_id)
    
    # Path to the special sequence script
    script_path = os.path.join(base_path, "special", "get_clipboard.py")
    
    # Run the special sequence
    try:
        result = subprocess.run(
            [sys.executable, script_path, adb_device_id, current_app],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting clipboard: {e}", file=sys.stderr)
        print(f"Error output: {e.stderr}", file=sys.stderr)
        return ""

def set_clipboard(device_id, content):
    """
    Set clipboard content on a device.
    
    Args:
        device_id: Device ID in any format (phoneX, IP:PORT, serial)
        content: Text content to set in clipboard
        
    Returns:
        True if successful, False otherwise
    """
    # Convert to ADB device ID format
    adb_device_id = get_adb_device_id(device_id)
    
    # Get the current app to return to
    current_app = get_current_app(adb_device_id)
    
    # Path to the special sequence script
    script_path = os.path.join(base_path, "special", "set_clipboard.py")
    
    # Run the special sequence
    try:
        result = subprocess.run(
            [sys.executable, script_path, adb_device_id, current_app, content],
            capture_output=True,
            text=True,
            check=True
        )
        return "successfully" in result.stdout.lower()
    except subprocess.CalledProcessError as e:
        print(f"Error setting clipboard: {e}", file=sys.stderr)
        print(f"Error output: {e.stderr}", file=sys.stderr)
        return False

# Example usage
if __name__ == "__main__":
    # This is just for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Test clipboard utilities")
    parser.add_argument("--device", default="phone1", help="Device ID")
    parser.add_argument("--get", action="store_true", help="Get clipboard content")
    parser.add_argument("--set", help="Set clipboard content")
    
    args = parser.parse_args()
    
    if args.get:
        content = get_clipboard(args.device)
        print(f"Clipboard content: {content}")
    
    if args.set:
        success = set_clipboard(args.device, args.set)
        if success:
            print(f"Successfully set clipboard content to: {args.set}")
        else:
            print("Failed to set clipboard content")

```

## connection_discord_bot_singleton.py

```python
import discord
from discord import app_commands
from discord.ext import tasks
from pathlib import Path
import os
import json
import asyncio
import datetime
import threading
from connection_manager import ConnectionManager
import time

# Discord bot configuration
DISCORD_TOKEN = "MTM0MjU4MTMyNTAxNzY0OTE3Mg.GFaUKh.6h2Ljs3boRwEc7evYcZ8kNtXyyd72RCEjxJnik"

class ConnectionBot(discord.Client):
    _instance = None
    _lock = threading.Lock()
    _bot_thread = None
    
    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance of ConnectionBot"""
        with cls._lock:
            if cls._instance is None:
                print("Initializing Discord bot...")
                cls._instance = cls()
                # Start the bot in a separate thread if not already running
                if cls._bot_thread is None or not cls._bot_thread.is_alive():
                    cls._bot_thread = threading.Thread(target=cls._instance._run_bot, daemon=True)
                    cls._bot_thread.start()
            return cls._instance
    
    def __init__(self):
        if self.__class__._instance is not None:
            raise RuntimeError("This class is a singleton! Use get_instance() instead.")
            
        # Enable all intents
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        
        self.status_file = Path(__file__).parent / "connection_status.txt"
        self.config_file = Path(__file__).parent / "discord_config.json"
        self.notification_channel_id = self.load_config().get('channel_id')
        self.tree = app_commands.CommandTree(self)
        
        # Initialize ConnectionManager
        self.connection_manager = None
        self.is_ready = threading.Event()
        
    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {}
        
    def save_config(self, channel_id):
        with open(self.config_file, 'w') as f:
            json.dump({'channel_id': channel_id}, f)
    
    def get_device_status(self):
        """Get the current status of all devices with timestamp"""
        # Format time as HH:MMam/pm
        current_time = datetime.datetime.now()
        hour = current_time.hour
        am_pm = "am" if hour < 12 else "pm"
        if hour > 12:
            hour -= 12
        if hour == 0:
            hour = 12
        formatted_time = f"{hour}:{current_time.minute:02d}{am_pm}"
        
        status_lines = [f"Current Device Status TIME ({formatted_time}):"]
        
        if self.connection_manager:
            current_devices = self.connection_manager.get_available_devices()
            
            # Show connected devices
            for name, info in current_devices.items():
                status_lines.append(f"+ {name} ({info['connection_type']} - {info['device_id']})")
                
            # Show disconnected devices
            for device_id, info in self.connection_manager.device_config["devices"].items():
                friendly_name = info["friendly_name"]
                if friendly_name not in current_devices:
                    status_lines.append(f"X {friendly_name}: disconnected")
        else:
            status_lines.append("ConnectionManager not initialized")
            
        return status_lines
    
    def send_notification(self, message):
        """Send a notification to the configured Discord channel
        
        This method can be called directly from other modules
        without needing to write to a file
        """
        if not self.is_ready.is_set():
            # If bot is not ready, write to file as fallback
            with open(self.status_file, "a") as f:
                f.write(f"{message}\n")
            return
            
        if not self.notification_channel_id:
            print("No notification channel configured")
            return
            
        asyncio.run_coroutine_threadsafe(
            self._send_notification_async(message),
            self.loop
        )
        
    async def _send_notification_async(self, message):
        """Internal async method to send notification"""
        try:
            channel = self.get_channel(self.notification_channel_id)
            if channel:
                # Format the message
                if ":" in message:
                    device, status = message.split(":", 1)
                    embed = discord.Embed(
                        title="Device Connection Changes",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name=device.strip(),
                        value=status.strip(),
                        inline=False
                    )
                    await channel.send(embed=embed)
                else:
                    await channel.send(message)
        except Exception as e:
            print(f"Error sending notification: {e}")
        
    async def setup_hook(self):
        # Register the slash command
        self.tree.add_command(app_commands.Command(
            name="status",
            description="Get the current status of all connected devices",
            callback=self.status_command
        ))
        await self.tree.sync()
        
        # Start the status check loop
        self.check_status.start()
        
    async def status_command(self, interaction):
        """Callback for the /status command"""
        await interaction.response.defer()
        
        # Initialize ConnectionManager if not already done
        if not self.connection_manager:
            self.connection_manager = ConnectionManager.get_instance()
            # Wait for ConnectionManager to initialize
            await asyncio.sleep(3)
            
        status_lines = self.get_device_status()
        
        # Create an embed for the response
        embed = discord.Embed(
            title="Device Status",
            description=status_lines[0],
            color=discord.Color.blue()
        )
        
        # Add connected and disconnected devices to the embed
        connected_devices = []
        disconnected_devices = []
        
        for line in status_lines[1:]:
            if line.startswith("+"):
                connected_devices.append(line[2:])  # Remove the "+ " prefix
            elif line.startswith("X"):
                disconnected_devices.append(line[2:])  # Remove the "X " prefix
                
        if connected_devices:
            embed.add_field(
                name="Connected Devices",
                value="\n".join(connected_devices),
                inline=False
            )
            
        if disconnected_devices:
            embed.add_field(
                name="Disconnected Devices",
                value="\n".join(disconnected_devices),
                inline=False
            )
            
        await interaction.followup.send(embed=embed)
        
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print(f'Bot ID: {self.user.id}')
        print('Permissions:')
        print('- Send Messages')
        print('- Embed Links')
        print('- Read Messages')
        print('\nUse !setchannel in your desired Discord channel to receive notifications')
        print('Use /status to get the current device status')
        
        # Initialize ConnectionManager
        self.connection_manager = ConnectionManager.get_instance()
        # Wait for ConnectionManager to initialize
        await asyncio.sleep(3)
        
        # Signal that the bot is ready
        self.is_ready.set()
        
    async def on_message(self, message):
        print(f"\nReceived message from {message.author} in {message.channel}:")
        print(f"Content: {message.content}")
        print(f"Channel ID: {message.channel.id}")
        
        if message.author == self.user:
            print("Message was from self, ignoring")
            return
            
        if message.content.startswith('!setchannel'):
            print(f"Setting channel to: {message.channel.id}")
            self.notification_channel_id = message.channel.id
            self.save_config(message.channel.id)
            try:
                await message.channel.send('I will send connection notifications to this channel')
                print("Successfully sent confirmation message")
            except Exception as e:
                print(f"Error sending confirmation: {e}")
                
    @tasks.loop(seconds=1.0)
    async def check_status(self):
        try:
            if self.status_file.exists():
                content = self.status_file.read_text()
                if content and self.notification_channel_id:
                    channel = self.get_channel(self.notification_channel_id)
                    if channel:
                        # Format the message
                        lines = content.strip().split("\n")
                        embed = discord.Embed(
                            title="Device Connection Changes",
                            color=discord.Color.blue()
                        )
                        
                        for line in lines:
                            if line:
                                device, status = line.split(":", 1)
                                embed.add_field(
                                    name=device.strip(),
                                    value=status.strip(),
                                    inline=False
                                )
                                
                        await channel.send(embed=embed)
                        
                    # Clear the file after processing
                    self.status_file.write_text("")
                    
        except Exception as e:
            print(f"Error checking status: {e}")
            
    @check_status.before_loop
    async def before_check_status(self):
        await self.wait_until_ready()
        
    def _run_bot(self):
        """Run the bot in a separate thread"""
        try:
            self.run(DISCORD_TOKEN)
        except Exception as e:
            print(f"Error running Discord bot: {e}")

def main():
    # Get singleton instance and wait for it to be ready
    bot = ConnectionBot.get_instance()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Bot shutdown requested")

if __name__ == "__main__":
    main()

```

## connection_manager.py

```python
import logging
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import subprocess
import time

class AccountError(Exception):
    """Base exception for account management errors"""
    pass

class ConfigError(AccountError):
    """Configuration related errors"""
    pass

class ConnectionManager:
    """Manages device connections and configurations. 
    This is a singleton to ensure only one instance manages device connections."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'ConnectionManager':
        """Get the singleton instance of ConnectionManager"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def __init__(self):
        """Initialize the ConnectionManager. Use get_instance() instead of calling directly."""
        if ConnectionManager._instance is not None:
            raise RuntimeError("ConnectionManager is a singleton. Use get_instance() instead.")
            
        ConnectionManager._instance = self
        
        # Initialize paths
        self.base_path = Path(__file__).parent.resolve()
        self.config_path = self.base_path / "config"
        self.log_path = self.base_path / "logs"
        self.adb_path = self.base_path / "platform-tools" / "adb.exe"
        
        # Create required directories
        self._setup_directories()
        
        # Initialize logging
        self._setup_logging()
        
        # Load configurations
        self.device_config_file = self.config_path / "device_config.json"
        self.client_config_file = self.config_path / "client_config.json"
        self.assignments_file = self.config_path / "account_assignments.json"
        
        self.device_config = self._load_device_config()
        self.client_config = self._load_client_config()
        self.account_assignments = self._load_assignments()
        
        # Initialize device service and client
        from services.device_service.service import DeviceService
        from services.device_service.client import DeviceServiceClient
        import time
        
        # First ensure ADB server is running
        try:
            subprocess.run([str(self.adb_path), "start-server"], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start ADB server: {e}")
            raise AccountError("Failed to start ADB server") from e
            
        # Get or start device service singleton
        try:
            self.device_service = DeviceService.get_instance()
            if not self.device_service.start():
                raise AccountError("Failed to start device service")
            
            # Give service time to initialize if just started
            if not self.device_service.running:
                time.sleep(2)
            
            # Connect client
            self.device_client = DeviceServiceClient()
            self.device_client.connect()
            
            self.logger.info("ConnectionManager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize device service: {e}")
            raise AccountError("Failed to initialize device service") from e

    def _setup_directories(self) -> None:
        """Create and verify required directories"""
        try:
            self.config_path.mkdir(parents=True, exist_ok=True)
            self.log_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ConfigError(f"Failed to create required directories: {str(e)}")

    def _setup_logging(self) -> None:
        """Configure account-specific logging"""
        log_file = self.log_path / "connection_manager.log"
        
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - ConnectionManager - %(message)s'
        )
        
        self.logger = logging.getLogger('ConnectionManager')
        self.logger.setLevel(logging.INFO)

    def _atomic_save(self, data: dict, file_path: Path) -> None:
        """Save configuration with atomic write"""
        temp_file = file_path.with_suffix('.tmp')
        try:
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=4)
            temp_file.replace(file_path)
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise ConfigError(f"Failed to save configuration: {str(e)}")

    def _load_device_config(self) -> Dict:
        """Load device configuration"""
        try:
            if self.device_config_file.exists():
                with open(self.device_config_file) as f:
                    return json.load(f)
        except Exception as e:
            raise ConfigError(f"Failed to load device config: {str(e)}")
        return {}

    def _load_client_config(self) -> Dict:
        """Load client configuration"""
        try:
            if self.client_config_file.exists():
                with open(self.client_config_file) as f:
                    return json.load(f)
        except Exception as e:
            raise ConfigError(f"Failed to load client config: {str(e)}")
        return {}

    def _load_assignments(self) -> Dict:
        """Load account assignments"""
        try:
            if self.assignments_file.exists():
                with open(self.assignments_file) as f:
                    return json.load(f)
        except Exception as e:
            raise ConfigError(f"Failed to load assignments: {str(e)}")
        return {"version": "1.0.0", "assignments": {}, "account_health": {}}

    def get_device_friendly_name(self, device_id: str) -> str:
        """Get friendly name for device"""
        device_info = self.device_config["devices"].get(device_id)
        if not device_info:
            raise ConfigError(f"Unknown device ID: {device_id}")
        return device_info["friendly_name"]

    def get_device_id(self, identifier: str) -> str:
        """Get device ID from friendly name or ID"""
        # If it's already a device ID, verify it exists
        if identifier in self.device_config["devices"]:
            return identifier
            
        # Look up by friendly name
        for device_id, info in self.device_config["devices"].items():
            if info["friendly_name"] == identifier:
                return device_id
                
        raise ConfigError(f"Unknown device: {identifier}")

    def get_client_profile(self, device_name: str) -> Dict:
        """Get client profile for device"""
        for client_info in self.client_config["clients"].values():
            if device_name in client_info["account_profiles"]:
                return client_info["account_profiles"][device_name]
        raise ConfigError(f"No profile found for device: {device_name}")

    def get_active_account(self, device_name: str) -> Optional[str]:
        """Get active account for device"""
        device_id = self.get_device_id(device_name)
        device_info = self.device_config["devices"][device_id]
        return device_info.get("active_account")

    def set_active_account(self, device_name: str, account_name: str) -> None:
        """Set active account for device"""
        device_id = self.get_device_id(device_name)
        self.device_config["devices"][device_id]["active_account"] = account_name
        self._atomic_save(self.device_config, self.device_config_file)

    def add_account(self, device_name: str, account_name: str, email: str) -> None:
        """Add new account to assignments"""
        device_id = self.get_device_id(device_name)
        client_name = "FanVue"  # Hardcoded for Phase 1
        
        # Add to assignments
        self.account_assignments["assignments"][account_name] = {
            "client": client_name,
            "device": device_name,
            "status": "active",
            "login_type": "email",
            "login_info": {
                "login": email,
                "password": self.get_client_profile(device_name)["profile_password"]
            }
        }
        
        # Initialize health tracking
        self.account_assignments["account_health"]["forced_logins"][account_name] = 0
        self.account_assignments["account_health"]["captchas"][account_name] = 0
        self.account_assignments["account_health"]["last_active"][account_name] = datetime.now().isoformat()
        
        # Save changes
        self._atomic_save(self.account_assignments, self.assignments_file)

    def update_health_metrics(self, device_name: str, account_name: str, metric_type: str, value: any) -> None:
        """Update health metrics for both device and account"""
        timestamp = datetime.now().isoformat()
        device_id = self.get_device_id(device_name)
        
        # Update device metrics
        device_metrics = self.device_config["device_health"]
        if metric_type not in device_metrics:
            device_metrics[metric_type] = {}
        device_metrics[metric_type][device_id] = value
        device_metrics["last_checked"][device_id] = timestamp
        
        # Update account metrics
        account_metrics = self.account_assignments["account_health"]
        if metric_type not in account_metrics:
            account_metrics[metric_type] = {}
        account_metrics[metric_type][account_name] = value
        account_metrics["last_active"][account_name] = timestamp
        
        # Save both configs
        self._atomic_save(self.device_config, self.device_config_file)
        self._atomic_save(self.account_assignments, self.assignments_file)

    def increment_health_counter(self, device_name: str, account_name: str, counter_type: str) -> None:
        """Increment health counter for both device and account"""
        device_id = self.get_device_id(device_name)
        
        # Update device counter
        device_metrics = self.device_config["device_health"]
        if counter_type not in device_metrics:
            device_metrics[counter_type] = {}
        if device_id not in device_metrics[counter_type]:
            device_metrics[counter_type][device_id] = 0
        device_metrics[counter_type][device_id] += 1
        
        # Update account counter
        account_metrics = self.account_assignments["account_health"]
        if counter_type not in account_metrics:
            account_metrics[counter_type] = {}
        if account_name not in account_metrics[counter_type]:
            account_metrics[counter_type][account_name] = 0
        account_metrics[counter_type][account_name] += 1
        
        # Update last checked/active timestamps
        timestamp = datetime.now().isoformat()
        device_metrics["last_checked"][device_id] = timestamp
        account_metrics["last_active"][account_name] = timestamp
        
        # Save both configs
        self._atomic_save(self.device_config, self.device_config_file)
        self._atomic_save(self.account_assignments, self.assignments_file)

    def get_available_devices(self) -> Dict[str, Dict]:
        """Get all available devices with connection info
        
        Returns a dict mapping friendly names to device info:
        {
            "friendly_name": {
                "device_id": str,      # ADB device ID
                "connection_type": str, # "wifi" or "usb"
                "active_account": str,  # Currently active account name
            }
        }
        """
        available = {}
        
        # Get WiFi devices from Device Service
        service_devices = self.device_service.get_devices()
        
        # Get USB devices directly from ADB
        try:
            result = subprocess.run(
                [str(self.adb_path), "devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            usb_devices = set()
            for line in result.stdout.splitlines()[1:]:
                if "\tdevice" in line:
                    device_id = line.split()[0]
                    if ":" not in device_id:  # Not a WiFi device
                        usb_devices.add(device_id)
        except Exception as e:
            self.logger.error(f"Error checking USB devices: {str(e)}")
            usb_devices = set()
        
        # Combine device info with config
        for device_id, info in self.device_config["devices"].items():
            friendly_name = info["friendly_name"]
            ip_address = info.get("ip_address")
            ip_with_port = f"{ip_address}:5555" if ip_address else None
            
            # Check if device is connected via WiFi through Device Service
            if ip_with_port and ip_with_port in service_devices:
                available[friendly_name] = {
                    "device_id": ip_with_port,
                    "connection_type": "wifi",
                    "active_account": info.get("active_account")
                }
                continue
            
            # Check if device is connected via USB
            if device_id in usb_devices:
                available[friendly_name] = {
                    "device_id": device_id,
                    "connection_type": "usb",
                    "active_account": info.get("active_account")
                }
        
        return available

```

## connection_monitor_updated.py

```python
import sys
import time
import logging
import datetime
from pathlib import Path
from typing import Dict, Optional
from connection_manager import ConnectionManager
from connection_discord_bot_singleton import ConnectionBot

class ConnectionMonitor:
    def __init__(self):
        try:
            print("Initializing ConnectionMonitor...")
            # Initialize paths
            self.base_path = Path(__file__).parent.resolve()
            self.logs_path = self.base_path / "logs"
            self.logs_path.mkdir(parents=True, exist_ok=True)
            
            # Get singleton instances
            self.connection_manager = ConnectionManager.get_instance()
            
            # Initialize Discord bot
            self.discord_bot = ConnectionBot.get_instance()
            
            self.setup_logging()
            self.last_status = {}
            self.last_heartbeat_time = 0
            print("ConnectionMonitor initialized successfully")
        except Exception as e:
            print(f"Failed to initialize ConnectionMonitor: {e}", file=sys.stderr)
            raise
        
    def setup_logging(self):
        log_file = self.logs_path / "connection_monitor.log"
        
        # Configure both file and console logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - ConnectionMonitor - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('ConnectionMonitor')
        
    def check_device_connections(self) -> Dict[str, Dict]:
        """Check current device connections and return status changes"""
        current_status = self.connection_manager.get_available_devices()
        changes = {}
        
        # Check for devices that were previously connected but are now disconnected
        for device_name in self.last_status:
            if device_name not in current_status:
                changes[device_name] = {
                    "status": "disconnected",
                    "previous": self.last_status[device_name]
                }
                
        # Check for new connections or connection type changes
        for device_name, info in current_status.items():
            if device_name not in self.last_status:
                changes[device_name] = {
                    "status": "connected",
                    "info": info
                }
            elif self.last_status[device_name] != info:
                changes[device_name] = {
                    "status": "changed",
                    "previous": self.last_status[device_name],
                    "current": info
                }
                
        self.last_status = current_status
        return changes

    def try_connect_wifi_devices(self):
        """Attempt to connect to known WiFi devices that aren't currently connected"""
        # Let ConnectionManager handle reconnection attempts
        # We just need to check for disconnections
        pass
        
    def try_connect_device(self, friendly_name: str, device_info: dict) -> bool:
        """Attempt to connect to a device and report failures
        
        Args:
            friendly_name: Name of the device (e.g. 'phone1')
            device_info: Device config info containing ip_address
            
        Returns:
            bool: True if connection successful, False if failed
        """
        if "ip_address" not in device_info:
            error_msg = f"{friendly_name}: No IP address configured"
            print(f"X {error_msg}")
            self.logger.error(error_msg)
            
            # Send notification directly to Discord
            self.discord_bot.send_notification(f"{friendly_name}: {error_msg}")
            return False
            
        ip_with_port = f"{device_info['ip_address']}:5555"
        print(f"Attempting to connect to {friendly_name} ({ip_with_port})...")
        
        try:
            result = self.connection_manager.device_service.connect_device(ip_with_port)
            if not result:
                error_msg = f"{friendly_name}: Failed to connect - device not responding"
                print(f"X {error_msg}")
                
                # Send notification directly to Discord
                self.discord_bot.send_notification(f"{friendly_name}: {error_msg}")
                return False
                
            print(f"+ Successfully connected to {friendly_name}")
            return True
            
        except Exception as e:
            error_msg = f"{friendly_name}: Connection error - {str(e)}"
            print(f"X {error_msg}")
            
            # Send notification directly to Discord
            self.discord_bot.send_notification(f"{friendly_name}: {error_msg}")
            return False
            
    def print_current_device_status(self):
        """Print the current status of all devices with timestamp"""
        # Format time as HH:MMam/pm
        current_time = datetime.datetime.now()
        hour = current_time.hour
        am_pm = "am" if hour < 12 else "pm"
        if hour > 12:
            hour -= 12
        if hour == 0:
            hour = 12
        formatted_time = f"{hour}:{current_time.minute:02d}{am_pm}"
        
        print(f"\nCurrent Device Status TIME ({formatted_time}):")
        current_devices = self.connection_manager.get_available_devices()
        
        # Show connected devices
        for name, info in current_devices.items():
            print(f"+ {name} ({info['connection_type']} - {info['device_id']})")
            
        # Show disconnected devices
        for device_id, info in self.connection_manager.device_config["devices"].items():
            friendly_name = info["friendly_name"]
            if friendly_name not in current_devices:
                print(f"X {friendly_name}: disconnected")
            
    def run(self, check_interval: int = 5):
        """Run the connection monitor with specified check interval"""
        print(f"\nStarting connection monitor with {check_interval} second interval...")
        self.logger.info("Starting connection monitor...")
        
        # Initial device check
        print("\nInitial device status:")
        current_devices = self.connection_manager.get_available_devices()
        
        # Show connected devices
        for name, info in current_devices.items():
            print(f"+ {name} ({info['connection_type']} - {info['device_id']})")
            
        # Try to connect any missing devices
        for device_id, info in self.connection_manager.device_config["devices"].items():
            friendly_name = info["friendly_name"]
            if friendly_name not in current_devices:
                print(f"X {friendly_name}: disconnected")
                if self.try_connect_device(friendly_name, info):
                    # If connection successful, add to current devices
                    current_devices[friendly_name] = {
                        "connection_type": "wifi",
                        "device_id": f"{info['ip_address']}:5555"
                    }
        
        print(f"\nMonitoring {len(current_devices)} connected devices...")
        print("Will notify about disconnections and connection failures\n")
        
        # Track last known status to detect disconnections
        last_known = current_devices
        
        while True:
            try:
                current_devices = self.connection_manager.get_available_devices()
                
                # Check for disconnections
                for name in last_known:
                    if name not in current_devices:
                        disconnect_msg = f"{name} disconnected"
                        print(f"! {disconnect_msg}")
                        
                        # Send notification directly to Discord
                        self.discord_bot.send_notification(f"{name}: disconnected")
                        
                        # Try to reconnect
                        device_info = None
                        for _, info in self.connection_manager.device_config["devices"].items():
                            if info["friendly_name"] == name:
                                device_info = info
                                break
                                
                        if device_info:
                            self.try_connect_device(name, device_info)
                
                # Update last known status
                last_known = current_devices
                
                # Print heartbeat status every 30 seconds
                current_time = time.time()
                if current_time - self.last_heartbeat_time >= 30:
                    self.print_current_device_status()
                    self.last_heartbeat_time = current_time
                
                time.sleep(check_interval)
                
            except Exception as e:
                error_msg = f"Error in connection monitor: {str(e)}"
                print(error_msg, file=sys.stderr)
                self.logger.error(error_msg)
                time.sleep(check_interval)

if __name__ == "__main__":
    monitor = ConnectionMonitor()
    time.sleep(3)  # Give ConnectionManager time to initialize
    monitor.run()

```

## core_device_ops.py

```python
#!/usr/bin/env python
"""
Core Device Operations Module
Provides basic ADB command execution and fundamental device interactions.
"""

import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict

from error_manager import ErrorManager, ErrorSeverity, ErrorCategory

class CoreDeviceOps:
    """
    Core device operations for interacting with Android devices via ADB.
    
    This class provides the fundamental operations needed to interact with
    an Android device, serving as the foundation for higher-level utilities.
    """
    
    def __init__(self, device_id: str, connection_manager=None):
        """
        Initialize device operations with a device ID
        
        Args:
            device_id: ADB device identifier
            connection_manager: Optional connection manager instance
        """
        if connection_manager is None:
            from connection_manager import ConnectionManager
            connection_manager = ConnectionManager.get_instance()
            
        self.connection_manager = connection_manager
        self.device_id = device_id
        
        # Initialize paths
        self.base_path = Path(__file__).parent.parent
        self.adb_path = self.base_path / "platform-tools" / "adb.exe"
        
        # Initialize error manager
        self.error_manager = ErrorManager(self.base_path)
        
        # Setup logging
        self.log_path = self.base_path / "logs"
        self.log_path.mkdir(exist_ok=True)
        
        # Create a unique logger instance for this device
        self.logger = logging.getLogger(f'Device_{device_id}')
        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_path / f"device_{device_id}.log")
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)

    def execute_command(self, command: List[str], binary_output: bool = False) -> Tuple[bool, bytes | str]:
        """
        Execute an ADB command with error handling
        
        Args:
            command: List of command arguments to pass to ADB
            binary_output: If True, return bytes output instead of decoded string
            
        Returns:
            Tuple of (success, output) where output is bytes or string based on binary_output
        """
        try:
            full_command = [str(self.adb_path), "-s", self.device_id] + command
            self.logger.info(f"Executing: {' '.join(full_command)}")
            
            result = subprocess.run(
                full_command,
                capture_output=True
            )
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, full_command)
                
            return True, result.stdout if binary_output else result.stdout.decode()
            
        except subprocess.CalledProcessError as e:
            self.error_manager.handle_error(
                device_name=self.device_id,
                error=e,
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.DEVICE
            )
            return False, b"" if binary_output else str(e)

    def screenshot(self, reason: str = "", max_retries: int = 3, retry_delay: float = 1.0) -> Optional[bytes]:
        """
        Take screenshot and return raw bytes with retry mechanism
        
        Args:
            reason: Optional reason for taking screenshot (for logs)
            max_retries: Number of attempts to make before giving up
            retry_delay: Seconds to wait between retries
            
        Returns:
            Raw screenshot data as bytes or None on failure
        """
        for attempt in range(max_retries):
            success, output = self.execute_command(["exec-out", "screencap -p"], binary_output=True)
            if success and output and len(output) > 1000:  # Ensure we got meaningful data
                return output
            
            if attempt < max_retries - 1:
                self.logger.warning(f"Screenshot attempt {attempt+1} failed or returned invalid data. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                
        self.logger.error(f"Failed to take screenshot after {max_retries} attempts")
        return None

    def tap(self, x: int, y: int) -> bool:
        """
        Execute tap at coordinates
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Tapping at coordinates: ({x}, {y})")
        return self.execute_command(["shell", f"input touchscreen tap {x} {y}"])[0]

    def key_event(self, keycode: int) -> bool:
        """
        Send keycode to device
        
        Args:
            keycode: Android keycode to send
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Sending keycode: {keycode}")
        return self.execute_command(["shell", f"input keyevent {keycode}"])[0]

    def navigate_back(self) -> bool:
        """
        Press back button (convenience method)
        
        Returns:
            True if successful, False otherwise
        """
        return self.key_event(4)  # KEYCODE_BACK = 4
        
    def sleep_device(self) -> bool:
        """
        Put device to sleep (turn off screen)
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Putting device {self.device_id} to sleep")
        return self.key_event(26)  # KEYCODE_POWER = 26
        
    def wake_device(self) -> bool:
        """
        Wake device (turn on screen)
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Waking device {self.device_id}")
        # Send WAKEUP keyevent
        success = self.key_event(224)  # KEYCODE_WAKEUP = 224
        
        if success:
            # Also send MENU key to ensure it's fully awake
            self.key_event(82)  # KEYCODE_MENU = 82
            
        return success

```

## device_config.json

```json
{
    "version": "1.0.0",
    "devices": {
        "R3CR40KCA8F": {
            "device_id": "R3CR40KCA8F",
            "friendly_name": "phone1",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.201"
        },
        "R5CR1296QHR": {
            "device_id": "R5CR1296QHR",
            "friendly_name": "phone2",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.202"
        },
        "R5CR12FQCXD": {
            "device_id": "R5CR12FQCXD",
            "friendly_name": "phone3",
            "status": "active",
            "tiktok_installed": "yes",
            "active_account": "JamesWilson467",
            "ip_address": "192.168.1.203"
        },
        "R5CR30857FV": {
            "device_id": "R5CR30857FV",
            "friendly_name": "phone4",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.204"
        },
        "R5CR30K10MF": {
            "device_id": "R5CR30K10MF",
            "friendly_name": "phone5",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.205"
        },
        "R5CR30MA1AB": {
            "device_id": "R5CR30MA1AB",
            "friendly_name": "phone6",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.206"
        },
        "R5CR60ZWY0T": {
            "device_id": "R5CR60ZWY0T",
            "friendly_name": "phone7",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.207"
        },
        "R5CR71E02DR": {
            "device_id": "R5CR71E02DR",
            "friendly_name": "phone8",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.208"
        },
        "R5CRC21J6LN": {
            "device_id": "R5CRC21J6LN",
            "friendly_name": "phone9",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.209"
        },
        "R5CR51424XR": {
            "device_id": "R5CR51424XR",
            "friendly_name": "phone10",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.210"
        },
        "R5CR5142JPA": {
            "device_id": "R5CR5142JPA",
            "friendly_name": "phone11",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.211"
        },
        "R5CR60KR2PB": {
            "device_id": "R5CR60KR2PB",
            "friendly_name": "phone12",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.212"
        },
        "R5CRA1YFD6W": {
            "device_id": "R5CRA1YFD6W",
            "friendly_name": "phone13",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.213"
        },
        "R5CRB1WD7QJ": {
            "device_id": "R5CRB1WD7QJ",
            "friendly_name": "phone14",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.214"
        },
        "R5CRB2DWD1V": {
            "device_id": "R5CRB2DWD1V",
            "friendly_name": "phone15",
            "status": "active",
            "tiktok_installed": "yes",
            "ip_address": "192.168.1.215"
        }
    },
    "last_phone_number": 15,
    "device_health": {
        "forced_logins": {
            "R5CR51424XR": [],
            "R5CR5142JPA": [],
            "R5CR60KR2PB": [],
            "R5CRA1YFD6W": [],
            "R5CRB1WD7QJ": [],
            "R5CRB2DWD1V": []
        },
        "captchas": {
            "R5CR51424XR": [],
            "R5CR5142JPA": [],
            "R5CR60KR2PB": [],
            "R5CRA1YFD6W": [],
            "R5CRB1WD7QJ": [],
            "R5CRB2DWD1V": []
        },
        "unknown_states": {
            "R5CR51424XR": [],
            "R5CR5142JPA": [],
            "R5CR60KR2PB": [],
            "R5CRA1YFD6W": [],
            "R5CRB1WD7QJ": [],
            "R5CRB2DWD1V": []
        },
        "errors": {
            "R5CR51424XR": [],
            "R5CR5142JPA": [],
            "R5CR60KR2PB": [],
            "R5CRA1YFD6W": [],
            "R5CRB1WD7QJ": [],
            "R5CRB2DWD1V": []
        },
        "last_checked": {
            "R5CR51424XR": "2024-12-23T13:32:42.733658",
            "R5CR5142JPA": "2024-12-23T13:33:52.193291",
            "R5CR60KR2PB": "2024-12-23T13:35:14.846605",
            "R5CRA1YFD6W": "2024-12-23T13:36:54.413244",
            "R5CRB1WD7QJ": "2024-12-23T13:38:49.009355",
            "R5CRB2DWD1V": "2024-12-23T13:39:40.958242"
        }
    }
}
```

## explorer_7.py

```python
import subprocess 
import json
import time
from datetime import datetime
from pathlib import Path 
from typing import Dict, Optional
import keyboard
from sequence_recorder import SequenceRecorder
from connection_manager import ConnectionManager
from utils.app_registry import AppRegistry

class ProcessExplorer:
    """Records complete interaction sequences including video and special operations"""
    
    def __init__(self):
        # Initialize paths
        self.base_path = Path(__file__).parent.resolve()
        self.logs_path = self.base_path / "logs"
        self.explorer_path = self.logs_path / "explorer"
        self.config_path = self.base_path / "config"
        
        # Ensure directories exist
        self.explorer_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize managers
        self.connection_manager = ConnectionManager.get_instance()
        
        # Session state
        self.current_session = None
        self.session_path = None
        self.recorder = None
        self.device_id = None
        
        # Configure keyboard hooks - only trigger with Ctrl
        keyboard.on_press(lambda e: self._handle_special_sequence() 
                         if keyboard.is_pressed('ctrl') and e.name == 's' else None)
        keyboard.on_press(lambda e: self._handle_clipboard_command() 
                         if keyboard.is_pressed('ctrl') and e.name == 't' else None)

    def get_devices(self) -> Dict[str, Dict]:
        """Get available connected devices"""
        return self.connection_manager.get_available_devices()
        
    def choose_device(self) -> Optional[str]:
        """Let user choose from available devices"""
        devices = self.get_devices()
        if not devices:
            print("\nNo devices connected!")
            print("Please check:")
            print("1. Devices are connected (USB or WiFi)")
            print("2. USB debugging is enabled")
            print("3. USB debugging authorization is granted")
            return None
            
        print("\nAvailable devices:")
        device_list = list(devices.items())
        for i, (device_name, info) in enumerate(device_list, 1):
            connection = info['connection_type'].upper()
            device_str = f"{i}. {device_name} ({connection} - {info['device_id']})"
            if info['active_account']:
                device_str += f"\n   Active Account: {info['active_account']}"
            print(device_str)
                
        while True:
            try:
                choice = input("\nSelect device number (or 'q' to quit): ").strip()
                if not choice or choice.lower() == 'q':
                    return None
                    
                choice_idx = int(choice)
                if 1 <= choice_idx <= len(device_list):
                    return device_list[choice_idx-1][1]['device_id']
                print("Invalid choice!")
            except ValueError:
                if choice.lower() != 'q':
                    print("Please enter a number!")
                    
    def start_session(self, process_name: str, app_name: str, device_id: str) -> bool:
        """Start new recording session"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            device_name = device_id.split(':')[0]  # Just use the IP/hostname part
            
            self.current_session = {
                "process": process_name,
                "app": app_name,
                "device_id": device_id,
                "device_name": device_name,
                "timestamp": timestamp
            }
            
            # Create session directory in logs/explorer
            self.session_path = self.explorer_path / process_name / timestamp
            self.session_path.mkdir(parents=True)
            
            # Initialize recorder
            self.device_id = device_id
            self.recorder = SequenceRecorder(device_id, self.base_path)
            
            print(f"\nStarting {app_name} process: {process_name}")
            print(f"Device: {device_name} ({device_id})")
            print(f"Saving to: {self.session_path}")
            print("\nAvailable commands:")
            print("Ctrl+S - Insert special sequence")
            print("Ctrl+T - Insert clipboard command")
            print("Ctrl+W - Mark next interaction as swipe")
            print("Ctrl+C - End recording")
            input("\nPress Enter to begin...")
            
            return self.recorder.start_recording(self.session_path)
            
        except Exception as e:
            print(f"Failed to start session: {str(e)}")
            return False

    def _handle_special_sequence(self):
        """Handle Ctrl+S for special sequence insertion"""
        if not self.recorder or not self.recorder.is_recording:
            return
                
        try:
            print("\nRecording paused for special sequence")
            
            # Disable keyboard hook while getting input
            keyboard.unhook_all()
            
            print("\nAvailable special sequences:")
            special_dir = self.base_path / "special"
            special_dir.mkdir(exist_ok=True)  # Ensure directory exists
            
            # List available special sequence modules
            sequences = []
            print("0. Create new sequence")
            for i, file_path in enumerate(special_dir.glob("*.py"), 1):
                if file_path.stem != "__init__":
                    sequences.append(file_path.stem)
                    print(f"{i}. {file_path.stem}")
                        
            # Get sequence choice
            while True:
                try:
                    choice = int(input("\nSelect sequence number: ").strip())
                    if choice == 0:
                        # Handle new sequence creation
                        module_name = input("Enter new sequence name (e.g. tiktok_birthday_spinner): ").strip()
                        if not module_name:
                            print("Module name cannot be empty!")
                            continue
                        class_name = ''.join(word.title() for word in module_name.split('_')) + 'Sequence'
                        description = input("Enter sequence description: ").strip()
                        
                        # Create placeholder file
                        new_file = special_dir / f"{module_name}.py"
                        if not new_file.exists():
                            template = f'''class {class_name}:
        """
        {description}
        TODO: Implement this special sequence
        """
        def __init__(self, device_id: str):
            self.device_id = device_id
            
        def execute_sequence(self) -> bool:
            """Execute the sequence"""
            # TODO: Implement sequence logic
            print("WARNING: {class_name} not yet implemented!")
            return False
    '''
                            new_file.write_text(template)
                            print(f"\nCreated placeholder file: {new_file}")
                        break
                        
                    elif 1 <= choice <= len(sequences):
                        module_name = sequences[choice-1]
                        # Convert module name to class name (e.g. open_wifi_settings -> OpenWifiSettingsSequence)
                        class_name = ''.join(word.title() for word in module_name.split('_')) + 'Sequence'
                        description = input("Enter sequence description: ").strip()
                        break
                    else:
                        print("Invalid choice!")
                except ValueError:
                    print("Please enter a number!")
                    continue
                
                
            # Pause recording
            self.recorder.pause_recording()
            
            print("Hit Enter once sequence complete")
            input()
            
            # Re-enable keyboard hook
            keyboard.on_press(lambda e: self._handle_special_sequence() 
                             if keyboard.is_pressed('ctrl') and e.name == 's' else None)
            keyboard.on_press(lambda e: self._handle_clipboard_command() 
                             if keyboard.is_pressed('ctrl') and e.name == 't' else None)
                
            # Add special sequence event
            event = {
                "name": f"Execute {module_name}",
                "description": description,
                "type": "special_sequence",
                "module": module_name,
                "class": class_name,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            self.recorder.add_event(event)
                
            self.recorder.resume_recording()
            print("Recording resumed")
                
        except Exception as e:
            print(f"Error handling special sequence: {str(e)}")

    def _handle_clipboard_command(self):
        """Handle Ctrl+T for clipboard command insertion"""
        if not self.recorder or not self.recorder.is_recording:
            return
            
        try:
            print("\nAvailable variables:")
            variables = self._get_account_variables()
            var_list = list(variables.items())
            
            for i, (var_name, value) in enumerate(var_list, 1):
                print(f"{i}. {var_name}: {value}")
                
            while True:
                try:
                    choice = int(input("\nSelect variable number: ").strip())
                    if choice == 0:
                        # Handle new variable creation
                        variable = input("Enter new variable name (e.g. personal.first_name): ").strip()
                        value = input("Enter variable value: ").strip()
                        break
                    elif 1 <= choice <= len(var_list):
                        variable, value = var_list[choice-1]
                        break
                    else:
                        print("Invalid choice!")
                except ValueError:
                    print("Please enter a number!")
                    continue
                    
            # Set clipboard on device
            self._set_device_clipboard(value)
            
            # Record command in sequence
            event = {
                "name": "Clipboard paste",
                "description": "",  # To be filled in later
                "type": "clipboard",
                "raw_text": value,
                "field_reference": variable,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            self.recorder.add_event(event)
            print(f"Added clipboard command: {variable}")
            
        except Exception as e:
            print(f"Error handling clipboard command: {str(e)}")

    def _get_account_variables(self) -> Dict[str, str]:
        """Get variables for current account"""
        variables = {}
        try:
            device_name = self.connection_manager.get_device_friendly_name(self.device_id)
            profile = self.connection_manager.get_client_profile(device_name)
            
            # Add personal info
            personal_info = profile["personal_info"]
            for field, value in personal_info.items():
                variables[f"personal.{field}"] = str(value)
                
            # Add account info
            active_account = self.connection_manager.get_active_account(device_name)
            if active_account:
                account_num = next(
                    (i for i, acc in enumerate(profile["accounts"]["tiktok"].items(), 1)
                     if acc[1]["username"] == active_account),
                    None
                )
                if account_num:
                    account_info = profile["accounts"]["tiktok"][f"account{account_num}"]
                    for field, value in account_info.items():
                        if isinstance(value, str):
                            variables[f"account.{field}"] = value
                            
        except Exception as e:
            print(f"Error getting account variables: {str(e)}")
            
        return variables

    def _set_device_clipboard(self, text: str) -> bool:
        """Set device clipboard content"""
        try:
            result = subprocess.run(
                [str(self.base_path / "platform-tools" / "adb.exe"),
                 "-s", self.device_id, "shell",
                 f"am broadcast -a clipper.set -e text '{text}'"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def end_session(self) -> bool:
        """End recording session and save data"""
        if not self.recorder:
            print("No active session!")
            return False
            
        try:
            # End recording session
            sequence_data = self.recorder.stop_recording()
            
            # Save sequence data
            sequence_file = self.session_path / "sequence.json"
            with open(sequence_file, "w") as f:
                json.dump(sequence_data, f, indent=4)
                
            print(f"\nSequence saved to: {sequence_file}")
            return True
            
        except Exception as e:
            print(f"Failed to save sequence: {str(e)}")
            return False

def main():
    explorer = ProcessExplorer()
    app_registry = AppRegistry.get_instance()
    
    try:
        print("\nSequence Explorer")
        print("================")
        
        # Get available devices
        device_id = explorer.choose_device()
        if not device_id:
            return
            
        # Get session info
        process = input("\nEnter process name (e.g., login_flow): ").strip()
        if not process:
            print("Process name required!")
            return
            
        # Get app from registry
        app_names = app_registry.get_all_app_names()
        if not app_names:
            print("No apps found in registry. Using manual input.")
            app = input("Enter app name (e.g., settings): ").strip()
        else:
            print("\nAvailable apps:")
            for i, app_name in enumerate(app_names, 1):
                app_info = app_registry.get_app_info(app_name)
                description = app_info.get("description", "")
                print(f"{i}. {app_name} - {description}")
                
            while True:
                try:
                    choice = int(input("\nSelect app number: ").strip())
                    if 1 <= choice <= len(app_names):
                        app = app_names[choice-1]
                        break
                    else:
                        print("Invalid choice!")
                except ValueError:
                    print("Please enter a number!")
                    continue
                    
        if not app:
            print("App name required!")
            return
            
        # Start recording session
        if not explorer.start_session(process, app, device_id):
            return
            
    finally:
        # Wait for completion
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nEnding recording...")
            explorer.end_session()
            print("\nSequence recording complete!")

if __name__ == "__main__":
    main()

```

## player_7.py

```python
import subprocess
import json
import time
from pathlib import Path
from typing import Dict
import importlib
from connection_manager import ConnectionManager
from utils.device_gestures import DeviceGestures

class SequencePlayer:
    def __init__(self, sequence_path: str, identifier: str = None):
        self.base_path = Path(__file__).parent
        self.adb_path = self.base_path / "platform-tools" / "adb.exe"
        self.sequence_path = Path(sequence_path)
        
        # Get connection manager
        self.connection_manager = ConnectionManager.get_instance()
        
        # Get device ID from identifier (could be friendly name or device ID)
        if identifier:
            self.device_id = self.connection_manager.get_device_id(identifier)
            if not self.device_id:
                raise ValueError(f"Could not find device: {identifier}")
        else:
            # Get first available device
            devices = self.connection_manager.get_available_devices()
            if not devices:
                raise ValueError("No devices connected")
            self.device_id = next(iter(devices.values()))["device_id"]
            
        # Initialize device gestures for humanized interactions
        self.gestures = DeviceGestures(self.device_id)
        
    def execute_command(self, command: list) -> bool:
        try:
            cmd = [str(self.adb_path), "-s", self.device_id] + command
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Command failed: {e}")
            return False

    def handle_special_sequence(self, event: Dict) -> bool:
        """Import and execute a special sequence"""
        try:
            print(f"\nExecuting special sequence: {event['module']}.{event['class']}")
            
            # Dynamically import the sequence module
            module_name = f"special.{event['module']}"
            sequence_module = importlib.import_module(module_name)
            
            # Get the sequence class
            sequence_class = getattr(sequence_module, event['class'])
            
            # Instantiate and execute
            sequence = sequence_class(self.device_id)
            success = sequence.execute_sequence()
            
            if success:
                print("Special sequence completed successfully")
            else:
                print("Special sequence failed!")
            
            return success
            
        except ImportError:
            print(f"Failed to import special sequence module: {event['module']}")
            return False
        except AttributeError:
            print(f"Failed to find sequence class: {event['class']}")
            return False
        except Exception as e:
            print(f"Error executing special sequence: {str(e)}")
            return False

    def play_sequence(self):
        """Play back sequence with natural timing"""
        try:
            # Load sequence
            with open(self.sequence_path) as f:
                sequence = json.load(f)
                
            print(f"\nPlaying sequence on {self.device_id}")
            
            # Track last event time for timing
            last_time = 0
            
            for event in sequence["events"]:
                # Standard delay between actions
                time.sleep(1.5)
                
                if event["type"] == "tap":
                    x, y = event["coordinates"]
                    print(f"\nExecuting tap at ({x}, {y})")
                    
                    # Use humanized tap with a small region around the target point
                    region = [x - 5, y - 5, x + 5, y + 5]
                    self.gestures.random_tap_in_region(region)
                    
                elif event["type"] == "swipe":
                    coords = event["coordinates"]
                    end = coords["end"]
                    duration = int(event["duration"] * 1000)  # Convert to milliseconds
                    if not coords["start"]:
                        print(f"\nWARNING: Swipe at ({end[0]}, {end[1]}) missing start coordinates")
                        print("Skipping swipe - please use swipe annotation tool first")
                        continue
                        
                    start = coords["start"]
                    print(f"\nExecuting swipe:")
                    print(f"From: ({start[0]}, {start[1]}) to ({end[0]}, {end[1]})")
                    print(f"Duration: {duration}ms")
                    
                    # Use humanized swipe with regions around start and end points
                    start_region = [start[0] - 5, start[1] - 5, start[0] + 5, start[1] + 5]
                    end_region = [end[0] - 5, end[1] - 5, end[0] + 5, end[1] + 5]
                    
                    # Ensure minimum duration of 100ms
                    self.gestures.swipe(start_region, end_region, max(duration, 100))
                    
                elif event["type"] == "special_sequence":
                    if not self.handle_special_sequence(event):
                        print("Special sequence failed - aborting sequence")
                        return False
                    
                elif event["type"] == "clipboard":
                    print(f"\nSetting clipboard: {event['field_reference']}")
                    self.execute_command([
                        "shell", "am", "broadcast",
                        "-a", "clipper.set",
                        "-e", "text", event["raw_text"]
                    ])
                    
            print("\nSequence complete!")
            return True
            
        except Exception as e:
            print(f"Error playing sequence: {e}")
            return False

def main():
    import sys
    if len(sys.argv) != 3:
        print("Usage: python sequence_player.py <sequence.json> <device>")
        return
        
    player = SequencePlayer(sys.argv[1], sys.argv[2])
    player.play_sequence()

if __name__ == "__main__":
    main()

```

## screen_verifier.py

```python
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

```

## swipe.py

```python
#!/usr/bin/env python
"""
Swipe Utility Module

Generates realistic human-like swipe events for Android devices.
This module implements natural swipe formulas based on statistical analysis
of real human touch gestures for different swipe types.
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

# Swipe type constants
DIRECTION_UP = "up"
DIRECTION_DOWN = "down"
DIRECTION_LEFT = "left"
DIRECTION_RIGHT = "right"

SPEED_SLOW = "slow"
SPEED_FAST = "fast"

LENGTH_SHORT = "short"
LENGTH_LONG = "long"

# Swipe parameters based on statistical analysis

# 1. Slow Short Up Swipe
SLOW_SHORT_UP_DURATION_MEAN = 467
SLOW_SHORT_UP_DURATION_STD = 94
SLOW_SHORT_UP_DURATION_MIN = 257
SLOW_SHORT_UP_DURATION_MAX = 710
SLOW_SHORT_UP_DISTANCE_MEAN = 328
SLOW_SHORT_UP_DISTANCE_STD = 50
SLOW_SHORT_UP_DISTANCE_MIN = 242
SLOW_SHORT_UP_DISTANCE_MAX = 446
SLOW_SHORT_UP_DEVIATION_MEAN = 0.0548

# 2. Slow Short Down Swipe
SLOW_SHORT_DOWN_DURATION_MEAN = 491
SLOW_SHORT_DOWN_DURATION_STD = 68
SLOW_SHORT_DOWN_DURATION_MIN = 334
SLOW_SHORT_DOWN_DURATION_MAX = 626
SLOW_SHORT_DOWN_DISTANCE_MEAN = 312
SLOW_SHORT_DOWN_DISTANCE_STD = 32
SLOW_SHORT_DOWN_DISTANCE_MIN = 239
SLOW_SHORT_DOWN_DISTANCE_MAX = 376
SLOW_SHORT_DOWN_DEVIATION_MEAN = 0.0435

# 3. Slow Long Up Swipe
SLOW_LONG_UP_DURATION_MEAN = 406
SLOW_LONG_UP_DURATION_STD = 145
SLOW_LONG_UP_DURATION_MIN = 133
SLOW_LONG_UP_DURATION_MAX = 700
SLOW_LONG_UP_DISTANCE_MEAN = 1827
SLOW_LONG_UP_DISTANCE_STD = 341
SLOW_LONG_UP_DISTANCE_MIN = 1075
SLOW_LONG_UP_DISTANCE_MAX = 2449
SLOW_LONG_UP_DEVIATION_MEAN = 0.0658

# 4. Slow Long Down Swipe
SLOW_LONG_DOWN_DURATION_MEAN = 457
SLOW_LONG_DOWN_DURATION_STD = 91
SLOW_LONG_DOWN_DURATION_MIN = 275
SLOW_LONG_DOWN_DURATION_MAX = 659
SLOW_LONG_DOWN_DISTANCE_MEAN = 1898
SLOW_LONG_DOWN_DISTANCE_STD = 329
SLOW_LONG_DOWN_DISTANCE_MIN = 1239
SLOW_LONG_DOWN_DISTANCE_MAX = 2553
SLOW_LONG_DOWN_DEVIATION_MEAN = 0.0388

# 5. Fast Short Up Flick
FAST_SHORT_UP_DURATION_MEAN = 83
FAST_SHORT_UP_DURATION_STD = 10
FAST_SHORT_UP_DURATION_MIN = 60
FAST_SHORT_UP_DURATION_MAX = 102
FAST_SHORT_UP_DISTANCE_MEAN = 264
FAST_SHORT_UP_DISTANCE_STD = 96
FAST_SHORT_UP_DISTANCE_MIN = 71
FAST_SHORT_UP_DISTANCE_MAX = 495
FAST_SHORT_UP_DEVIATION_MEAN = 0.0340

# 6. Fast Short Down Flick
FAST_SHORT_DOWN_DURATION_MEAN = 93
FAST_SHORT_DOWN_DURATION_STD = 10
FAST_SHORT_DOWN_DURATION_MIN = 75
FAST_SHORT_DOWN_DURATION_MAX = 117
FAST_SHORT_DOWN_DISTANCE_MEAN = 326
FAST_SHORT_DOWN_DISTANCE_STD = 72
FAST_SHORT_DOWN_DISTANCE_MIN = 167
FAST_SHORT_DOWN_DISTANCE_MAX = 503
FAST_SHORT_DOWN_DEVIATION_MEAN = 0.0232

# 7. Fast Long Up Flick
FAST_LONG_UP_DURATION_MEAN = 79
FAST_LONG_UP_DURATION_STD = 16
FAST_LONG_UP_DURATION_MIN = 41
FAST_LONG_UP_DURATION_MAX = 117
FAST_LONG_UP_DISTANCE_MEAN = 1341
FAST_LONG_UP_DISTANCE_STD = 431
FAST_LONG_UP_DISTANCE_MIN = 464
FAST_LONG_UP_DISTANCE_MAX = 2427
FAST_LONG_UP_DEVIATION_MEAN = 0.0485

# 8. Fast Long Down Flick
FAST_LONG_DOWN_DURATION_MEAN = 57
FAST_LONG_DOWN_DURATION_STD = 10
FAST_LONG_DOWN_DURATION_MIN = 33
FAST_LONG_DOWN_DURATION_MAX = 85
FAST_LONG_DOWN_DISTANCE_MEAN = 1802
FAST_LONG_DOWN_DISTANCE_STD = 348
FAST_LONG_DOWN_DISTANCE_MIN = 975
FAST_LONG_DOWN_DISTANCE_MAX = 2567
FAST_LONG_DOWN_DEVIATION_MEAN = 0.0638

# 9. Left Swipe
LEFT_DURATION_MEAN = 105
LEFT_DURATION_STD = 13
LEFT_DURATION_MIN = 75
LEFT_DURATION_MAX = 144
LEFT_DISTANCE_MEAN = 979
LEFT_DISTANCE_STD = 304
LEFT_DISTANCE_MIN = 446
LEFT_DISTANCE_MAX = 1706
LEFT_DEVIATION_MEAN = 0.0057

# 10. Right Swipe
RIGHT_DURATION_MEAN = 130
RIGHT_DURATION_STD = 25
RIGHT_DURATION_MIN = 77
RIGHT_DURATION_MAX = 184
RIGHT_DISTANCE_MEAN = 1245
RIGHT_DISTANCE_STD = 252
RIGHT_DISTANCE_MIN = 689
RIGHT_DISTANCE_MAX = 1900
RIGHT_DEVIATION_MEAN = 0.0092


def generate_swipe_events(
    device_id: str,
    region: List[int],
    direction: str,
    speed: str = SPEED_SLOW,
    length: str = LENGTH_SHORT,
    use_core_ops: bool = True
) -> Union[bool, List[Dict[str, Any]]]:
    """
    Generate and optionally execute a realistic human-like swipe within the specified region.
    
    Args:
        device_id: ADB device ID (e.g., 192.168.1.201:5555)
        region: [x_min, y_min, x_max, y_max] region to swipe within
        direction: Direction of swipe (up, down, left, right)
        speed: Speed of swipe (slow, fast)
        length: Length of swipe (short, long) - only applicable for vertical swipes
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
    
    # Validate direction
    if direction not in [DIRECTION_UP, DIRECTION_DOWN, DIRECTION_LEFT, DIRECTION_RIGHT]:
        print(f"Invalid direction: {direction}. Expected one of: up, down, left, right")
        return False if use_core_ops else []
    
    # Validate speed
    if speed not in [SPEED_SLOW, SPEED_FAST]:
        print(f"Invalid speed: {speed}. Expected one of: slow, fast")
        return False if use_core_ops else []
    
    # Validate length (only applicable for vertical swipes)
    if length not in [LENGTH_SHORT, LENGTH_LONG]:
        print(f"Invalid length: {length}. Expected one of: short, long")
        return False if use_core_ops else []
    
    # Select a random point within the region
    start_x = random.randint(x_min, x_max)
    start_y = random.randint(y_min, y_max)
    
    # Determine swipe parameters based on direction, speed, and length
    if direction == DIRECTION_UP:
        if speed == SPEED_SLOW:
            if length == LENGTH_SHORT:
                # Slow Short Up Swipe
                duration_mean = SLOW_SHORT_UP_DURATION_MEAN
                duration_std = SLOW_SHORT_UP_DURATION_STD
                duration_min = SLOW_SHORT_UP_DURATION_MIN
                duration_max = SLOW_SHORT_UP_DURATION_MAX
                distance_mean = SLOW_SHORT_UP_DISTANCE_MEAN
                distance_std = SLOW_SHORT_UP_DISTANCE_STD
                distance_min = SLOW_SHORT_UP_DISTANCE_MIN
                distance_max = SLOW_SHORT_UP_DISTANCE_MAX
                deviation_mean = SLOW_SHORT_UP_DEVIATION_MEAN
            else:
                # Slow Long Up Swipe
                duration_mean = SLOW_LONG_UP_DURATION_MEAN
                duration_std = SLOW_LONG_UP_DURATION_STD
                duration_min = SLOW_LONG_UP_DURATION_MIN
                duration_max = SLOW_LONG_UP_DURATION_MAX
                distance_mean = SLOW_LONG_UP_DISTANCE_MEAN
                distance_std = SLOW_LONG_UP_DISTANCE_STD
                distance_min = SLOW_LONG_UP_DISTANCE_MIN
                distance_max = SLOW_LONG_UP_DISTANCE_MAX
                deviation_mean = SLOW_LONG_UP_DEVIATION_MEAN
        else:  # SPEED_FAST
            if length == LENGTH_SHORT:
                # Fast Short Up Flick
                duration_mean = FAST_SHORT_UP_DURATION_MEAN
                duration_std = FAST_SHORT_UP_DURATION_STD
                duration_min = FAST_SHORT_UP_DURATION_MIN
                duration_max = FAST_SHORT_UP_DURATION_MAX
                distance_mean = FAST_SHORT_UP_DISTANCE_MEAN
                distance_std = FAST_SHORT_UP_DISTANCE_STD
                distance_min = FAST_SHORT_UP_DISTANCE_MIN
                distance_max = FAST_SHORT_UP_DISTANCE_MAX
                deviation_mean = FAST_SHORT_UP_DEVIATION_MEAN
            else:
                # Fast Long Up Flick
                duration_mean = FAST_LONG_UP_DURATION_MEAN
                duration_std = FAST_LONG_UP_DURATION_STD
                duration_min = FAST_LONG_UP_DURATION_MIN
                duration_max = FAST_LONG_UP_DURATION_MAX
                distance_mean = FAST_LONG_UP_DISTANCE_MEAN
                distance_std = FAST_LONG_UP_DISTANCE_STD
                distance_min = FAST_LONG_UP_DISTANCE_MIN
                distance_max = FAST_LONG_UP_DISTANCE_MAX
                deviation_mean = FAST_LONG_UP_DEVIATION_MEAN
    elif direction == DIRECTION_DOWN:
        if speed == SPEED_SLOW:
            if length == LENGTH_SHORT:
                # Slow Short Down Swipe
                duration_mean = SLOW_SHORT_DOWN_DURATION_MEAN
                duration_std = SLOW_SHORT_DOWN_DURATION_STD
                duration_min = SLOW_SHORT_DOWN_DURATION_MIN
                duration_max = SLOW_SHORT_DOWN_DURATION_MAX
                distance_mean = SLOW_SHORT_DOWN_DISTANCE_MEAN
                distance_std = SLOW_SHORT_DOWN_DISTANCE_STD
                distance_min = SLOW_SHORT_DOWN_DISTANCE_MIN
                distance_max = SLOW_SHORT_DOWN_DISTANCE_MAX
                deviation_mean = SLOW_SHORT_DOWN_DEVIATION_MEAN
            else:
                # Slow Long Down Swipe
                duration_mean = SLOW_LONG_DOWN_DURATION_MEAN
                duration_std = SLOW_LONG_DOWN_DURATION_STD
                duration_min = SLOW_LONG_DOWN_DURATION_MIN
                duration_max = SLOW_LONG_DOWN_DURATION_MAX
                distance_mean = SLOW_LONG_DOWN_DISTANCE_MEAN
                distance_std = SLOW_LONG_DOWN_DISTANCE_STD
                distance_min = SLOW_LONG_DOWN_DISTANCE_MIN
                distance_max = SLOW_LONG_DOWN_DISTANCE_MAX
                deviation_mean = SLOW_LONG_DOWN_DEVIATION_MEAN
        else:  # SPEED_FAST
            if length == LENGTH_SHORT:
                # Fast Short Down Flick
                duration_mean = FAST_SHORT_DOWN_DURATION_MEAN
                duration_std = FAST_SHORT_DOWN_DURATION_STD
                duration_min = FAST_SHORT_DOWN_DURATION_MIN
                duration_max = FAST_SHORT_DOWN_DURATION_MAX
                distance_mean = FAST_SHORT_DOWN_DISTANCE_MEAN
                distance_std = FAST_SHORT_DOWN_DISTANCE_STD
                distance_min = FAST_SHORT_DOWN_DISTANCE_MIN
                distance_max = FAST_SHORT_DOWN_DISTANCE_MAX
                deviation_mean = FAST_SHORT_DOWN_DEVIATION_MEAN
            else:
                # Fast Long Down Flick
                duration_mean = FAST_LONG_DOWN_DURATION_MEAN
                duration_std = FAST_LONG_DOWN_DURATION_STD
                duration_min = FAST_LONG_DOWN_DURATION_MIN
                duration_max = FAST_LONG_DOWN_DURATION_MAX
                distance_mean = FAST_LONG_DOWN_DISTANCE_MEAN
                distance_std = FAST_LONG_DOWN_DISTANCE_STD
                distance_min = FAST_LONG_DOWN_DISTANCE_MIN
                distance_max = FAST_LONG_DOWN_DISTANCE_MAX
                deviation_mean = FAST_LONG_DOWN_DEVIATION_MEAN
    elif direction == DIRECTION_LEFT:
        # Left Swipe (horizontal swipes don't have length distinction)
        duration_mean = LEFT_DURATION_MEAN
        duration_std = LEFT_DURATION_STD
        duration_min = LEFT_DURATION_MIN
        duration_max = LEFT_DURATION_MAX
        distance_mean = LEFT_DISTANCE_MEAN
        distance_std = LEFT_DISTANCE_STD
        distance_min = LEFT_DISTANCE_MIN
        distance_max = LEFT_DISTANCE_MAX
        deviation_mean = LEFT_DEVIATION_MEAN
    else:  # DIRECTION_RIGHT
        # Right Swipe (horizontal swipes don't have length distinction)
        duration_mean = RIGHT_DURATION_MEAN
        duration_std = RIGHT_DURATION_STD
        duration_min = RIGHT_DURATION_MIN
        duration_max = RIGHT_DURATION_MAX
        distance_mean = RIGHT_DISTANCE_MEAN
        distance_std = RIGHT_DISTANCE_STD
        distance_min = RIGHT_DISTANCE_MIN
        distance_max = RIGHT_DISTANCE_MAX
        deviation_mean = RIGHT_DEVIATION_MEAN
    
    # Generate duration with normal distribution
    duration_ms = random.normalvariate(duration_mean, duration_std)
    duration_ms = max(duration_min, min(duration_ms, duration_max))  # Clamp to observed range
    
    # Generate distance with normal distribution
    distance = random.normalvariate(distance_mean, distance_std)
    distance = max(distance_min, min(distance, distance_max))  # Clamp to observed range
    
    # Calculate end coordinates based on direction and distance
    if direction == DIRECTION_UP:
        # For up swipes, decrease y-coordinate
        end_y = max(y_min, start_y - distance)
        
        # Add realistic path deviation to x-coordinate
        # Up swipes typically curve "left then right"
        deviation = distance * deviation_mean
        deviation_factor = random.uniform(0.5, 1.5)  # Add some randomness to deviation
        end_x = start_x + int(deviation * deviation_factor)
        
        # Ensure end_x is within the region bounds
        end_x = max(x_min, min(end_x, x_max))
        
    elif direction == DIRECTION_DOWN:
        # For down swipes, increase y-coordinate
        end_y = min(y_max, start_y + distance)
        
        # Add realistic path deviation to x-coordinate
        # Down swipes typically curve "right then left"
        deviation = distance * deviation_mean
        deviation_factor = random.uniform(0.5, 1.5)  # Add some randomness to deviation
        end_x = start_x - int(deviation * deviation_factor)
        
        # Ensure end_x is within the region bounds
        end_x = max(x_min, min(end_x, x_max))
        
    elif direction == DIRECTION_LEFT:
        # For left swipes, decrease x-coordinate
        end_x = max(x_min, start_x - distance)
        
        # Add realistic path deviation to y-coordinate
        deviation = distance * deviation_mean
        deviation_factor = random.uniform(0.5, 1.5)  # Add some randomness to deviation
        end_y = start_y + int(deviation * deviation_factor)
        
        # Ensure end_y is within the region bounds
        end_y = max(y_min, min(end_y, y_max))
        
    else:  # DIRECTION_RIGHT
        # For right swipes, increase x-coordinate
        end_x = min(x_max, start_x + distance)
        
        # Add realistic path deviation to y-coordinate
        deviation = distance * deviation_mean
        deviation_factor = random.uniform(0.5, 1.5)  # Add some randomness to deviation
        end_y = start_y - int(deviation * deviation_factor)
        
        # Ensure end_y is within the region bounds
        end_y = max(y_min, min(end_y, y_max))
    
    # If not using CoreDeviceOps, return the event parameters
    if not use_core_ops:
        return [{
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "duration_ms": int(duration_ms)
        }]
    
    # Initialize CoreDeviceOps
    core_ops = CoreDeviceOps(device_id)
    
    # Use input swipe command to execute the swipe
    cmd = f"input swipe {start_x} {start_y} {end_x} {end_y} {int(duration_ms)}"
    result, _ = core_ops.execute_command(["shell", cmd])
    
    return result


if __name__ == "__main__":
    # This is just for testing and should not be used directly
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate realistic swipe gestures")
    parser.add_argument("--device", required=True, help="Device ID")
    parser.add_argument("--region", required=True, type=str, help="Region as x_min,y_min,x_max,y_max")
    parser.add_argument("--direction", required=True, choices=["up", "down", "left", "right"], help="Swipe direction")
    parser.add_argument("--speed", default="slow", choices=["slow", "fast"], help="Swipe speed")
    parser.add_argument("--length", default="short", choices=["short", "long"], help="Swipe length (for vertical swipes)")
    
    args = parser.parse_args()
    
    region = [int(x) for x in args.region.split(",")]
    
    result = generate_swipe_events(
        device_id=args.device,
        region=region,
        direction=args.direction,
        speed=args.speed,
        length=args.length
    )
    
    print(f"Swipe {'succeeded' if result else 'failed'}")

```

## tap.py

```python
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

```

## test_special.py

```python
#!/usr/bin/env python
"""
Test script for running scripts from the 'special' directory on selected devices.
Allows selection of a connected device and a script to run.
"""

import os
import sys
import time
import importlib.util
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from connection_manager import ConnectionManager

def get_available_devices() -> Dict[str, dict]:
    """
    Get all available devices through ConnectionManager.
    
    Returns:
        Dict mapping friendly names to device info.
    """
    connection_manager = ConnectionManager.get_instance()
    
    # Wait 3 seconds for ConnectionManager to initialize
    print("Initializing ConnectionManager...")
    time.sleep(3)
    
    # Get all available devices
    devices = connection_manager.get_available_devices()
    
    return devices

def get_special_scripts() -> List[Path]:
    """
    Get all Python scripts in the special directory.
    
    Returns:
        List of Path objects for Python scripts in the special directory.
    """
    special_dir = Path(__file__).parent.parent / "special"
    scripts = list(special_dir.glob("*.py"))
    
    # Filter out __init__.py and __pycache__ files
    scripts = [s for s in scripts if not s.name.startswith("__")]
    
    return sorted(scripts)

def select_from_options(options: List[Tuple[str, str]], prompt: str) -> Optional[str]:
    """
    Present a numbered list of options to the user and get their selection.
    
    Args:
        options: List of (value, display_text) tuples
        prompt: Text to show when asking for selection
    
    Returns:
        The selected value or None if selection failed
    """
    if not options:
        print("No options available.")
        return None
    
    print("\n" + prompt)
    print("=" * len(prompt))
    
    for i, (_, display_text) in enumerate(options, 1):
        print(f"{i}. {display_text}")
    
    try:
        choice = input("\nEnter number (or 'q' to quit): ")
        if choice.lower() == 'q':
            return None
        
        index = int(choice) - 1
        if 0 <= index < len(options):
            return options[index][0]
        else:
            print(f"Invalid choice. Please enter a number between 1 and {len(options)}.")
            return select_from_options(options, prompt)
    except ValueError:
        print("Please enter a number.")
        return select_from_options(options, prompt)

def run_script_with_device(script_path: Path, device_id: str) -> bool:
    """
    Run a script from the special directory with the specified device ID.
    
    Args:
        script_path: Path to the script to run
        device_id: Device ID to pass to the script
    
    Returns:
        True if successful, False otherwise
    """
    try:
        script_name = script_path.stem
        print(f"\nRunning '{script_name}' with device '{device_id}'...\n")
        
        # Run the script directly with the device ID as an argument
        # This assumes all special scripts are designed to take a device_id as their only argument
        result = subprocess.run(
            [sys.executable, str(script_path), device_id],
            check=False
        )
        
        if result.returncode == 0:
            print(f"\nScript '{script_name}' completed successfully.")
            return True
        else:
            print(f"\nScript '{script_name}' failed with exit code {result.returncode}.")
            return False
            
    except Exception as e:
        print(f"Error running script: {e}")
        return False

def main():
    """Main entry point."""
    try:
        print("\nSpecial Script Runner")
        print("====================")
        
        # Get available devices
        print("\nGetting available devices...")
        devices = get_available_devices()
        
        if not devices:
            print("\nNo devices found. Please connect a device and try again.")
            return
        
        # Format device options for selection
        device_options = []
        for friendly_name, info in devices.items():
            device_id = info.get('device_id', '')
            device_options.append((device_id, f"{friendly_name} ({device_id})"))
        
        # Let user select a device
        selected_device = select_from_options(device_options, "Select a device")
        if not selected_device:
            print("\nNo device selected. Exiting.")
            return
        
        # Get scripts from special directory
        scripts = get_special_scripts()
        
        if not scripts:
            print("\nNo scripts found in the 'special' directory.")
            return
        
        # Format script options for selection
        script_options = []
        for script in scripts:
            # Read the first docstring line if available
            description = ""
            try:
                spec = importlib.util.spec_from_file_location(script.stem, script)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if module.__doc__:
                    description = f" - {module.__doc__.strip().split('\n')[0]}"
            except:
                pass
            
            script_options.append((str(script), f"{script.stem}{description}"))
        
        # Let user select a script
        selected_script = select_from_options(script_options, "Select a script to run")
        if not selected_script:
            print("\nNo script selected. Exiting.")
            return
        
        # Run the selected script with the selected device
        run_script_with_device(Path(selected_script), selected_device)
        
    except KeyboardInterrupt:
        print("\nOperation interrupted. Exiting.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()

```

## type.py

```python
#!/usr/bin/env python3
"""
Utility for typing text on a device with realistic input behavior.
Automatically selects between typing, dictation, and autofill based on content.
"""

import random
import time
import re
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union, Any

# Add the project root to the path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.device_id_converter import get_ip_from_device_id
import keyboard_client

# Constants for typing simulation
TYPING_DELAY_RANGE = (0.032, 0.125)  # Base delay range between keypresses in seconds (based on tap duration analysis)
DICTATION_WORD_DELAY_RANGE = (0.2, 0.5)  # Delay between words in dictation
AUTOFILL_PROBABILITY = 0.2  # Probability of using autofill for eligible content
DICTATION_PROBABILITY = 0.15  # Probability of using dictation for eligible content
TYPO_PROBABILITY = 0.2  # Probability of making a typo for a word
AUTOCORRECT_PROBABILITY = 0.9  # Probability that autocorrect will fix a typo
BURST_TYPING_PROBABILITY = 0.7  # Probability of typing common words faster
BURST_TYPING_MODIFIER = 0.6  # Speed modifier for burst typing (lower = faster)
CAPITAL_LETTER_MODIFIER = 2.15  # Delay modifier for capital letters (except at start of sentence)
SPECIAL_CHAR_MODIFIER = (2.0, 3.0)  # Range of delay modifiers for special characters

# Tap movement parameters from statistical analysis
TAP_MOVEMENT_DISTANCE_MEAN = 12.01  # pixels
TAP_MOVEMENT_DISTANCE_STD = 9.16
TAP_MOVEMENT_DX_MEAN = -1.51  # pixels
TAP_MOVEMENT_DX_STD = 13.57
TAP_MOVEMENT_DY_MEAN = 0.87  # pixels
TAP_MOVEMENT_DY_STD = 6.40

# Quadrant distribution for movement direction
TAP_QUADRANT_PROBS = {
    'Q1 (right-down)': 0.3006,  # +x, +y
    'Q2 (left-down)': 0.3121,   # -x, +y
    'Q3 (left-up)': 0.2197,     # -x, -y
    'Q4 (right-up)': 0.1676     # +x, -y
}

# Common words that might be typed faster
COMMON_WORDS = {
    "the", "and", "a", "to", "of", "in", "is", "it", "you", "that", "he", "was", "for", 
    "on", "are", "with", "as", "I", "his", "they", "be", "at", "one", "have", "this", 
    "from", "or", "had", "by", "not", "word", "but", "what", "some", "we", "can", "out", 
    "other", "were", "all", "there", "when", "up", "use", "your", "how", "said", "an", 
    "each", "she", "which", "do", "their", "time", "if", "will", "way", "about", "many", 
    "then", "them", "write", "would", "like", "so", "these", "her", "long", "make", 
    "thing", "see", "him", "two", "has", "look", "more", "day", "could", "go", "come", 
    "did", "number", "sound", "no", "most", "people", "my", "over", "know", "water", 
    "than", "call", "first", "who", "may", "down", "side", "been", "now", "find", "any", 
    "new", "work", "part", "take", "get", "place", "made", "live", "where", "after", 
    "back", "little", "only", "round", "man", "year", "came", "show", "every", "good", 
    "me", "give", "our", "under", "name", "very", "through", "just", "form", "sentence", 
    "great", "think", "say", "help", "low", "line", "differ", "turn", "cause", "much", 
    "mean", "before", "move", "right", "boy", "old", "too", "same", "tell", "does", 
    "set", "three", "want", "air", "well", "also", "play", "small", "end", "put", "home", 
    "read", "hand", "port", "large", "spell", "add", "even", "land", "here", "must", 
    "big", "high", "such", "follow", "act", "why", "ask", "men", "change", "went", 
    "light", "kind", "off", "need", "house", "picture", "try", "us", "again", "animal", 
    "point", "mother", "world", "near", "build", "self", "earth", "father", "head", 
    "stand", "own", "page", "should", "country", "found", "answer", "school", "grow", 
    "study", "still", "learn", "plant", "cover", "food", "sun", "four", "between", 
    "state", "keep", "eye", "never", "last", "let", "thought", "city", "tree", "cross", 
    "farm", "hard", "start", "might", "story", "saw", "far", "sea", "draw", "left", 
    "late", "run", "don't", "while", "press", "close", "night", "real", "life", "few", 
    "north", "open", "seem", "together", "next", "white", "children", "begin", "got", 
    "walk", "example", "ease", "paper", "group", "always", "music", "those", "both", 
    "mark", "often", "letter", "until", "mile", "river", "car", "feet", "care", "second", 
    "book", "carry", "took", "science", "eat", "room", "friend", "began", "idea", "fish", 
    "mountain", "stop", "once", "base", "hear", "horse", "cut", "sure", "watch", "color", 
    "face", "wood", "main", "enough", "plain", "girl", "usual", "young", "ready", "above", 
    "ever", "red", "list", "though", "feel", "talk", "bird", "soon", "body", "dog", 
    "family", "direct", "pose", "leave", "song", "measure", "door", "product", "black", 
    "short", "numeral", "class", "wind", "question", "happen", "complete", "ship", "area", 
    "half", "rock", "order", "fire", "south", "problem", "piece", "told", "knew", "pass", 
    "since", "top", "whole", "king", "space", "heard", "best", "hour", "better", "true", 
    "during", "hundred", "five", "remember", "step", "early", "hold", "west", "ground", 
    "interest", "reach", "fast", "verb", "sing", "listen", "six", "table", "travel", 
    "less", "morning", "ten", "simple", "several", "vowel", "toward", "war", "lay", 
    "against", "pattern", "slow", "center", "love", "person", "money", "serve", "appear", 
    "road", "map", "rain", "rule", "govern", "pull", "cold", "notice", "voice", "unit", 
    "power", "town", "fine", "certain", "fly", "fall", "lead", "cry", "dark", "machine", 
    "note", "wait", "plan", "figure", "star", "box", "noun", "field", "rest", "correct", 
    "able", "pound", "done", "beauty", "drive", "stood", "contain", "front", "teach", 
    "week", "final", "gave", "green", "oh", "quick", "develop", "ocean", "warm", "free", 
    "minute", "strong", "special", "mind", "behind", "clear", "tail", "produce", "fact", 
    "street", "inch", "multiply", "nothing", "course", "stay", "wheel", "full", "force", 
    "blue", "object", "decide", "surface", "deep", "moon", "island", "foot", "system", 
    "busy", "test", "record", "boat", "common", "gold", "possible", "plane", "stead", 
    "dry", "wonder", "laugh", "thousand", "ago", "ran", "check", "game", "shape", 
    "equate", "hot", "miss", "brought", "heat", "snow", "tire", "bring", "yes", "distant", 
    "fill", "east", "paint", "language", "among", "grand", "ball", "yet", "wave", "drop", 
    "heart", "am", "present", "heavy", "dance", "engine", "position", "arm", "wide", 
    "sail", "material", "size", "vary", "settle", "speak", "weight", "general", "ice", 
    "matter", "circle", "pair", "include", "divide", "syllable", "felt", "perhaps", 
    "pick", "sudden", "count", "square", "reason", "length", "represent", "art", "subject", 
    "region", "energy", "hunt", "probable", "bed", "brother", "egg", "ride", "cell", 
    "believe", "fraction", "forest", "sit", "race", "window", "store", "summer", "train", 
    "sleep", "prove", "lone", "leg", "exercise", "wall", "catch", "mount", "wish", 
    "sky", "board", "joy", "winter", "sat", "written", "wild", "instrument", "kept", 
    "glass", "grass", "cow", "job", "edge", "sign", "visit", "past", "soft", "fun", 
    "bright", "gas", "weather", "month", "million", "bear", "finish", "happy", "hope", 
    "flower", "clothe", "strange", "gone", "jump", "baby", "eight", "village", "meet", 
    "root", "buy", "raise", "solve", "metal", "whether", "push", "seven", "paragraph", 
    "third", "shall", "held", "hair", "describe", "cook", "floor", "either", "result", 
    "burn", "hill", "safe", "cat", "century", "consider", "type", "law", "bit", "coast", 
    "copy", "phrase", "silent", "tall", "sand", "soil", "roll", "temperature", "finger", 
    "industry", "value", "fight", "lie", "beat", "excite", "natural", "view", "sense", 
    "ear", "else", "quite", "broke", "case", "middle", "kill", "son", "lake", "moment", 
    "scale", "loud", "spring", "observe", "child", "straight", "consonant", "nation", 
    "dictionary", "milk", "speed", "method", "organ", "pay", "age", "section", "dress", 
    "cloud", "surprise", "quiet", "stone", "tiny", "climb", "cool", "design", "poor", 
    "lot", "experiment", "bottom", "key", "iron", "single", "stick", "flat", "twenty", 
    "skin", "smile", "crease", "hole", "trade", "melody", "trip", "office", "receive", 
    "row", "mouth", "exact", "symbol", "die", "least", "trouble", "shout", "except", 
    "wrote", "seed", "tone", "join", "suggest", "clean", "break", "lady", "yard", "rise", 
    "bad", "blow", "oil", "blood", "touch", "grew", "cent", "mix", "team", "wire", "cost", 
    "lost", "brown", "wear", "garden", "equal", "sent", "choose", "fell", "fit", "flow", 
    "fair", "bank", "collect", "save", "control", "decimal", "gentle", "woman", "captain", 
    "practice", "separate", "difficult", "doctor", "please", "protect", "noon", "whose", 
    "locate", "ring", "character", "insect", "caught", "period", "indicate", "radio", 
    "spoke", "atom", "human", "history", "effect", "electric", "expect", "crop", "modern", 
    "element", "hit", "student", "corner", "party", "supply", "bone", "rail", "imagine", 
    "provide", "agree", "thus", "capital", "won't", "chair", "danger", "fruit", "rich", 
    "thick", "soldier", "process", "operate", "guess", "necessary", "sharp", "wing", 
    "create", "neighbor", "wash", "bat", "rather", "crowd", "corn", "compare", "poem", 
    "string", "bell", "depend", "meat", "rub", "tube", "famous", "dollar", "stream", 
    "fear", "sight", "thin", "triangle", "planet", "hurry", "chief", "colony", "clock", 
    "mine", "tie", "enter", "major", "fresh", "search", "send", "yellow", "gun", "allow", 
    "print", "dead", "spot", "desert", "suit", "current", "lift", "rose", "continue", 
    "block", "chart", "hat", "sell", "success", "company", "subtract", "event", 
    "particular", "deal", "swim", "term", "opposite", "wife", "shoe", "shoulder", "spread", 
    "arrange", "camp", "invent", "cotton", "born", "determine", "quart", "nine", "truck", 
    "noise", "level", "chance", "gather", "shop", "stretch", "throw", "shine", "property", 
    "column", "molecule", "select", "wrong", "gray", "repeat", "require", "broad", "prepare", 
    "salt", "nose", "plural", "anger", "claim", "continent", "oxygen", "sugar", "death", 
    "pretty", "skill", "women", "season", "solution", "magnet", "silver", "thank", "branch", 
    "match", "suffix", "especially", "fig", "afraid", "huge", "sister", "steel", "discuss", 
    "forward", "similar", "guide", "experience", "score", "apple", "bought", "led", "pitch", 
    "coat", "mass", "card", "band", "rope", "slip", "win", "dream", "evening", "condition", 
    "feed", "tool", "total", "basic", "smell", "valley", "nor", "double", "seat", "arrive", 
    "master", "track", "parent", "shore", "division", "sheet", "substance", "favor", 
    "connect", "post", "spend", "chord", "fat", "glad", "original", "share", "station", 
    "dad", "bread", "charge", "proper", "bar", "offer", "segment", "slave", "duck", 
    "instant", "market", "degree", "populate", "chick", "dear", "enemy", "reply", "drink", 
    "occur", "support", "speech", "nature", "range", "steam", "motion", "path", "liquid", 
    "log", "meant", "quotient", "teeth", "shell", "neck"
}

# Common homophones for dictation errors
COMMON_HOMOPHONES = {
    "there": ["their", "they're"],
    "their": ["there", "they're"],
    "they're": ["their", "there"],
    "your": ["you're", "you've"],
    "you're": ["your", "you've"],
    "its": ["it's"],
    "it's": ["its"],
    "were": ["we're", "where"],
    "we're": ["were", "where"],
    "where": ["were", "we're"],
    "than": ["then"],
    "then": ["than"],
    "affect": ["effect"],
    "effect": ["affect"],
    "to": ["too", "two"],
    "too": ["to", "two"],
    "two": ["to", "too"],
    "accept": ["except"],
    "except": ["accept"],
    "weather": ["whether"],
    "whether": ["weather"],
    "hear": ["here"],
    "here": ["hear"],
    "break": ["brake"],
    "brake": ["break"],
    "piece": ["peace"],
    "peace": ["piece"],
    "principal": ["principle"],
    "principle": ["principal"],
    "complement": ["compliment"],
    "compliment": ["complement"],
    "desert": ["dessert"],
    "dessert": ["desert"],
    "capital": ["capitol"],
    "capitol": ["capital"],
    "stair": ["stare"],
    "stare": ["stair"],
    "sight": ["site", "cite"],
    "site": ["sight", "cite"],
    "cite": ["site", "sight"],
    "coarse": ["course"],
    "course": ["coarse"],
    "aloud": ["allowed"],
    "allowed": ["aloud"],
    "bear": ["bare"],
    "bare": ["bear"],
    "board": ["bored"],
    "bored": ["board"],
    "cereal": ["serial"],
    "serial": ["cereal"],
    "fair": ["fare"],
    "fare": ["fair"],
    "great": ["grate"],
    "grate": ["great"],
    "grown": ["groan"],
    "groan": ["grown"],
    "heal": ["heel"],
    "heel": ["heal"],
    "heard": ["herd"],
    "herd": ["heard"],
    "hour": ["our"],
    "our": ["hour"],
    "knight": ["night"],
    "night": ["knight"],
    "knot": ["not"],
    "not": ["knot"],
    "know": ["no"],
    "no": ["know"],
    "made": ["maid"],
    "maid": ["made"],
    "mail": ["male"],
    "male": ["mail"],
    "meat": ["meet"],
    "meet": ["meat"],
    "morning": ["mourning"],
    "mourning": ["morning"],
    "pair": ["pear", "pare"],
    "pear": ["pair", "pare"],
    "pare": ["pair", "pear"],
    "plain": ["plane"],
    "plane": ["plain"],
    "rain": ["reign", "rein"],
    "reign": ["rain", "rein"],
    "rein": ["rain", "reign"],
    "role": ["roll"],
    "roll": ["role"],
    "sail": ["sale"],
    "sale": ["sail"],
    "scene": ["seen"],
    "seen": ["scene"],
    "some": ["sum"],
    "sum": ["some"],
    "son": ["sun"],
    "sun": ["son"],
    "steal": ["steel"],
    "steel": ["steal"],
    "tail": ["tale"],
    "tale": ["tail"],
    "wait": ["weight"],
    "weight": ["wait"],
    "way": ["weigh"],
    "weigh": ["way"],
    "weak": ["week"],
    "week": ["weak"],
    "wear": ["where"],
    "where": ["wear"],
    "which": ["witch"],
    "witch": ["which"],
    "wood": ["would"],
    "would": ["wood"]
}

# Common typos for realistic typing errors
COMMON_TYPOS = {
    # Transposition errors (swapped letters)
    "the": ["teh"],
    "and": ["adn"],
    "for": ["fro"],
    "with": ["wiht"],
    "this": ["tihs"],
    "that": ["taht"],
    "what": ["waht"],
    "when": ["wehn"],
    "where": ["wehre"],
    "would": ["woudl"],
    "could": ["cuold"],
    "should": ["shuold"],
    "because": ["becuase"],
    "people": ["peopel"],
    "about": ["abuot"],
    
    # Common misspellings
    "definitely": ["definately", "definatly", "defenitely"],
    "separate": ["seperate", "seperete"],
    "necessary": ["neccessary", "necessery"],
    "receive": ["recieve"],
    "believe": ["beleive"],
    "accommodate": ["accomodate", "acommodate"],
    "occurrence": ["occurence", "occurrance"],
    "restaurant": ["restaraunt", "resteraunt"],
    "immediately": ["immediatly", "immedietly"],
    "government": ["goverment", "govenment"],
    "beginning": ["begining", "beggining"],
    "weird": ["wierd"],
    "successful": ["succesful", "successfull"],
    "tomorrow": ["tommorow", "tommorrow"],
    "surprise": ["suprise", "surprize"],
    "familiar": ["familar", "familliar"],
    "different": ["diffrent", "diferent"],
    "probably": ["probly", "probaly"],
    "thought": ["thougt", "thougth"],
    "business": ["busness", "bussiness"],
    "beautiful": ["beutiful", "beautifull"],
    "exercise": ["excercise", "exercize"],
    "address": ["adress", "adres"],
    "calendar": ["calender", "calander"],
    "friend": ["freind", "frend"],
    "embarrass": ["embarass", "embaras"],
    "grammar": ["grammer", "gramar"],
    "privilege": ["priviledge", "privilage"],
    "recommend": ["reccomend", "recomend"],
    "relevant": ["relevent", "revelant"],
    "schedule": ["schedual", "shedule"],
    "argument": ["arguement", "arguemnet"],
    "environment": ["enviroment", "enviornment"],
    "experience": ["experiance", "expereince"],
    "library": ["libary", "liberry"],
    "maintenance": ["maintainance", "maintnance"],
    "occasion": ["ocassion", "occassion"],
    "occurred": ["occured", "ocurred"],
    "particular": ["particuler", "partikular"],
    "rhythm": ["rythm", "rythem"],
    "surprise": ["suprise", "surprize"],
    "until": ["untill", "untl"],
    "vacuum": ["vacume", "vaccuum"],
    "vehicle": ["vehical", "vehicel"],
    "weather": ["wether", "wheather"],
    "writing": ["writting", "writeing"],
}

# Common autocorrect failures (wrong word suggestions)
AUTOCORRECT_FAILS = {
    "were": "we're",
    "well": "we'll",
    "cant": "can't",
    "wont": "won't",
    "its": "it's",
    "your": "you're",
    "their": "there",
    "there": "their",
    "then": "than",
    "than": "then",
    "affect": "effect",
    "effect": "affect",
    "accept": "except",
    "except": "accept",
    "to": "too",
    "too": "to",
    "hear": "here",
    "here": "hear",
    "break": "brake",
    "brake": "break",
    "principal": "principle",
    "principle": "principal",
    "desert": "dessert",
    "dessert": "desert",
    "stationary": "stationery",
    "stationery": "stationary",
    "complement": "compliment",
    "compliment": "complement",
    "capital": "capitol",
    "capitol": "capital",
    "cite": "site",
    "site": "cite",
    "council": "counsel",
    "counsel": "council",
    "coarse": "course",
    "course": "coarse",
}

def type_text(
    device_id: str,
    region: List[int],
    text: str,
    mode: Optional[str] = None,
) -> bool:
    """
    Type text on a device using the most appropriate method based on content.
    
    Args:
        device_id: ADB device ID
        region: Region to type in [x1, y1, x2, y2]
        text: Text to type
        mode: Optional override for input mode ('typing', 'dictation', 'autofill')
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Get IP address for keyboard communication
        ip_port = get_ip_from_device_id(device_id)
        if not ip_port or ":" not in ip_port:
            print(f"Failed to get valid IP:PORT from device ID: {device_id}")
            return False
            
        ip, port_str = ip_port.split(":")
        port = int(port_str)
        
        # Tap in the provided region
        from utils.tap import generate_tap_events
        tap_result = generate_tap_events(device_id, region)
        if not tap_result:
            print(f"Failed to tap in region {region}")
            return False
                
        time.sleep(0.5)  # Wait for keyboard to appear
        
        # If mode is explicitly specified, use that
        if mode:
            if mode == "typing":
                return _handle_typing(ip, port, text)
            elif mode == "dictation":
                return _handle_dictation(ip, port, text)
            elif mode == "autofill":
                return _handle_autofill(ip, port, text)
            else:
                print(f"Invalid mode: {mode}")
                return False
        
        # Otherwise, automatically select the best mode based on content
        
        # Check if text is suitable for autofill (short phrases, common expressions)
        autofill_patterns = [
            r"^(Yes|No|Maybe|Sure|Okay|OK|Thanks|Thank you|Hello|Hi|Hey|Bye|Goodbye|See you|Later)$",
            r"^(I agree|I disagree|I understand|I don't know|I'm not sure|I think so|I don't think so)$",
            r"^(Good morning|Good afternoon|Good evening|Good night)$",
            r"^(How are you|What's up|What are you doing|Where are you|When will you|Why did you)$",
            r"^(Can you|Could you|Would you|Will you|Should I|Can I|May I)$",
            r"^(That's great|That's awesome|That's cool|That's nice|That's interesting|That's funny)$",
            r"^(I'll call you|I'll text you|I'll be there|I'll do it|I'll try|I'll see)$",
            r"^(On my way|Be right there|Just a minute|Give me a second|Hold on|Wait)$",
            r"^(Let me know|Keep me posted|Tell me more|Sounds good|Works for me)$",
            r"^(See you soon|Talk to you later|Catch you later|Until next time)$"
        ]
        
        is_autofill_candidate = any(re.match(pattern, text) for pattern in autofill_patterns)
        
        # Check for @ symbol in a single word (email addresses, usernames)
        is_at_symbol_word = len(text.split()) == 1 and '@' in text
        if is_at_symbol_word:
            is_autofill_candidate = True
        
        # Decide if this is a good candidate for dictation
        # Longer text, complete sentences, proper punctuation
        is_dictation_candidate = (
            len(text) > 50 and  # Longer text
            len(text.split()) > 10 and  # Multiple words
            any(p in text for p in ['.', '!', '?']) and  # Contains sentence endings
            text[0].isupper()  # Starts with capital letter
        )
        
        # Make probabilistic decision based on text characteristics
        if is_dictation_candidate and random.random() < 0.8:  # 80% chance for dictation if candidate
            return _handle_dictation(ip, port, text)
        elif is_autofill_candidate and random.random() < 0.7:  # 70% chance for autofill if candidate
            return _handle_autofill(ip, port, text)
        else:
            # Default to typing
            return _handle_typing(ip, port, text)
            
    except Exception as e:
        print(f"Error in type_text: {e}")
        return False

def type_text_sequence(
    device_id: str,
    region: List[int],
    text: str,
    mode: Optional[str] = None,
) -> bool:
    """
    Type text on a device using a sequence-based approach for improved accuracy.
    
    Args:
        device_id: Device ID to type on
        region: Region to tap in [x1, y1, x2, y2]
        text: Text to type
        mode: Force a specific typing mode (typing, dictation, autofill)
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Convert device ID to IP:PORT format for keyboard client
        ip_port = get_ip_from_device_id(device_id)
        ip, port = ip_port.split(':')
        port = int(port)
        
        # First tap in the region to ensure focus
        from utils.tap import generate_tap_events
        tap_result = generate_tap_events(device_id, region)
        if not tap_result:
            print(f"Failed to tap in region {region}")
            return False
        
        # Wait for tap to register
        time.sleep(0.5)
        
        # Build the sequence based on the selected mode
        if mode == "typing" or mode is None:
            sequence = _build_typing_sequence(text)
        elif mode == "dictation":
            sequence = _build_dictation_sequence(text)
        elif mode == "autofill":
            sequence = _build_autofill_sequence(text)
        else:
            # Default to typing
            sequence = _build_typing_sequence(text)
        
        # Execute the sequence
        response = keyboard_client.execute_sequence(ip, port, sequence)
        
        # Check if the sequence executed successfully
        if response.get("status") == "success":
            return True
        else:
            print(f"Error executing sequence: {response.get('message', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"Error in type_text_sequence: {e}")
        return False

def _handle_typing(ip: str, port: int, text: str) -> bool:
    """
    Simulate realistic typing with human-like patterns.
    
    Args:
        ip: Device IP address
        port: Device port
        text: Text to type
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Split text into words and spaces
        words = re.findall(r'\S+|\s+', text)
        
        # Track state for autocorrect failures
        wrong_autocorrect_word = None
        wrong_autocorrect_index = -1
        
        # Track if we're at the start of a sentence (for auto-capitalization)
        start_of_sentence = True
        
        for i, word in enumerate(words):
            # Handle spaces
            if word.isspace():
                keyboard_client.type_text(ip, port, " ")
                time.sleep(random.uniform(0.05, 0.15))
                continue
            
            # Check if we need to fix a previous wrong autocorrect
            if wrong_autocorrect_word is not None and i - wrong_autocorrect_index >= 2 and random.random() < 0.9:
                # Calculate how many characters to delete (including spaces)
                chars_to_delete = sum(len(words[j]) for j in range(wrong_autocorrect_index + 1, i + 1))
                
                # Add spaces between words
                chars_to_delete += (i - wrong_autocorrect_index)
                
                # Delete back to the error
                keyboard_client.delete_text(ip, port, chars_to_delete)
                time.sleep(random.uniform(0.2, 0.4))
                
                # Type the correct word
                keyboard_client.type_text(ip, port, wrong_autocorrect_word)
                
                # Add a space
                keyboard_client.type_text(ip, port, " ")
                
                # Now retype the deleted words
                for j in range(wrong_autocorrect_index + 1, i + 1):
                    keyboard_client.type_text(ip, port, words[j])
                    
                    # Add space if not the last word
                    if j < i:
                        keyboard_client.type_text(ip, port, " ")
                
                # Reset wrong autocorrect tracking
                wrong_autocorrect_word = None
                wrong_autocorrect_index = -1
                
                # Continue with the next word
                continue
            
            # Decide if we'll make a typo for this word
            make_typo = random.random() < TYPO_PROBABILITY and len(word) > 1 and not any(c in word for c in "@#$%^&*()_+-=[]{}|;:'\",.<>/?\\")
            
            # Check if this is a common word that might be typed quickly
            is_common_word = word.lower() in COMMON_WORDS and random.random() < BURST_TYPING_PROBABILITY
            
            if make_typo:
                # Generate a typo
                typo = _generate_typo(word)
                
                # Type the typo character by character with realistic timing
                for j, char in enumerate(typo):
                    # Determine typing speed based on character type
                    if is_common_word:
                        # Burst typing for common words
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * BURST_TYPING_MODIFIER
                    elif char.isalpha() and char.islower():
                        # Common lowercase letters
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char.isalpha() and char.isupper() and not start_of_sentence:
                        # Capital letters (except at start of sentence)
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * CAPITAL_LETTER_MODIFIER
                    elif char.isalpha() and char.isupper() and start_of_sentence:
                        # First letter of sentence is auto-capitalized, no extra delay
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char.isdigit():
                        # Numbers
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char in ".,":
                        # Common punctuation
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char in "!@#$%^&*()_+-=[]{}|;:'\",<>/?\\":
                        # Special characters
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0] * SPECIAL_CHAR_MODIFIER[0], 
                                                  TYPING_DELAY_RANGE[1] * SPECIAL_CHAR_MODIFIER[1])
                    else:
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    
                    # Add variation based on tap movement statistics
                    movement_factor = random.normalvariate(1.0, 0.15)  # 15% variation based on movement
                    adjusted_delay = base_delay * movement_factor
                    
                    # Type the character
                    keyboard_client.type_text(ip, port, char)
                    time.sleep(adjusted_delay)
                
                # Decide if autocorrect will fix the typo
                if random.random() < AUTOCORRECT_PROBABILITY:
                    # Simulate autocorrect behavior
                    time.sleep(random.uniform(0.2, 0.4))  # Brief pause for autocorrect
                    
                    # Delete the typo
                    keyboard_client.delete_text(ip, port, len(typo))
                    time.sleep(random.uniform(0.1, 0.2))
                    
                    # Get a replacement (sometimes wrong)
                    replacement = _get_autocorrect_replacement(word, typo)
                    
                    # Type the replacement
                    keyboard_client.type_text(ip, port, replacement)
                    
                    # If the replacement is wrong, track it for potential later correction
                    if replacement != word:
                        wrong_autocorrect_word = word
                        wrong_autocorrect_index = i
                else:
                    # No autocorrect, the typo remains
                    pass
            else:
                # No typo, type the word normally
                for j, char in enumerate(word):
                    # Determine typing speed based on character type
                    if is_common_word:
                        # Burst typing for common words
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * BURST_TYPING_MODIFIER
                    elif char.isalpha() and char.islower():
                        # Common lowercase letters
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char.isalpha() and char.isupper() and not start_of_sentence:
                        # Capital letters (except at start of sentence)
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * CAPITAL_LETTER_MODIFIER
                    elif char.isalpha() and char.isupper() and start_of_sentence:
                        # First letter of sentence is auto-capitalized, no extra delay
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char.isdigit():
                        # Numbers
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char in ".,":
                        # Common punctuation
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char in "!@#$%^&*()_+-=[]{}|;:'\",<>/?\\":
                        # Special characters
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0] * SPECIAL_CHAR_MODIFIER[0], 
                                                  TYPING_DELAY_RANGE[1] * SPECIAL_CHAR_MODIFIER[1])
                    else:
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    
                    # Add variation based on tap movement statistics
                    movement_factor = random.normalvariate(1.0, 0.15)  # 15% variation based on movement
                    adjusted_delay = base_delay * movement_factor
                    
                    # Type the character
                    keyboard_client.type_text(ip, port, char)
                    time.sleep(adjusted_delay)
            
            # Add a space after the word (unless it's the last word)
            if i < len(words) - 1 and not words[i+1].isspace():
                keyboard_client.type_text(ip, port, " ")
                time.sleep(random.uniform(0.05, 0.15))
            
            # Update sentence tracking
            if word.endswith(('.', '!', '?')):
                start_of_sentence = True
            else:
                start_of_sentence = False
            
            # Add occasional thinking pauses between words with more realistic distribution
            pause_chance = random.random()
            if pause_chance < 0.15:  # 15% chance of a pause
                if pause_chance < 0.03:  # 3% chance of a longer thinking pause
                    time.sleep(random.uniform(0.8, 2.0))
                else:  # 12% chance of a shorter pause
                    time.sleep(random.uniform(0.2, 0.5))
        
        return True
        
    except Exception as e:
        print(f"Error in _handle_typing: {e}")
        return False

def _handle_dictation(ip: str, port: int, text: str) -> bool:
    """
    Simulate dictation with realistic word timing, errors, and corrections.
    
    Args:
        ip: Device IP address
        port: Device port
        text: Text to dictate
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for sentence_idx, sentence in enumerate(sentences):
            # Simulate thinking before dictating
            if sentence_idx > 0:
                time.sleep(random.uniform(1.0, 2.0))
            
            # Split sentence into words
            words = sentence.split()
            
            # Track dictation errors for potential correction
            error_index = -1
            original_word = None
            
            for i, word in enumerate(words):
                # Decide if we'll make a dictation error
                make_error = random.random() < 0.15 and len(word) > 2
                
                if make_error and word.lower() in COMMON_HOMOPHONES:
                    # Use a homophone instead
                    original_word = word
                    error_index = i
                    error_word = random.choice(COMMON_HOMOPHONES[word.lower()])
                    
                    # Maintain capitalization
                    if word[0].isupper():
                        error_word = error_word[0].upper() + error_word[1:]
                    
                    # Type the error word
                    keyboard_client.type_text(ip, port, error_word)
                elif make_error and len(word) > 4:
                    # Make up a plausible dictation error
                    original_word = word
                    
                    # Different types of errors
                    error_type = random.choice(["similar", "compound_split", "join"])
                    
                    if error_type == "similar":
                        # Replace with a similar-sounding word
                        similar_words = {
                            "their": "there", "there": "their", "they're": "their",
                            "your": "you're", "you're": "your", "its": "it's", "it's": "its",
                            "affect": "effect", "effect": "affect", "then": "than", "than": "then",
                            "accept": "except", "except": "accept", "lose": "loose", "loose": "lose",
                            "weather": "whether", "whether": "weather", "to": "too", "too": "to",
                            "hear": "here", "here": "hear", "right": "write", "write": "right"
                        }
                        
                        if word.lower() in similar_words:
                            error_word = similar_words[word.lower()]
                            # Preserve capitalization
                            if word[0].isupper():
                                error_word = error_word[0].upper() + error_word[1:]
                        else:
                            # Just use the original word
                            error_word = word
                            error_index = -1  # Reset since we didn't make an error
                    elif error_type == "compound_split" and len(word) > 5:
                        # Only split at realistic compound word boundaries
                        compound_splits = {
                            "keyboard": "key board",
                            "notebook": "note book",
                            "background": "back ground",
                            "sometimes": "some times",
                            "everything": "every thing",
                            "something": "some thing",
                            "anything": "any thing",
                            "nothing": "no thing",
                            "downtown": "down town",
                            "bedroom": "bed room",
                            "bathroom": "bath room",
                            "classroom": "class room",
                            "football": "foot ball",
                            "baseball": "base ball",
                            "basketball": "basket ball",
                            "weekend": "week end",
                            "birthday": "birth day",
                            "sunlight": "sun light",
                            "moonlight": "moon light",
                            "daylight": "day light",
                            "software": "soft ware",
                            "hardware": "hard ware",
                            "firewall": "fire wall",
                            "network": "net work",
                            "website": "web site",
                            "homepage": "home page",
                            "username": "user name",
                            "password": "pass word",
                            "database": "data base",
                            "filename": "file name",
                            "keyboard": "key board",
                            "smartphone": "smart phone",
                            "headphone": "head phone",
                            "microphone": "micro phone",
                            "loudspeaker": "loud speaker",
                            "toothbrush": "tooth brush",
                            "toothpaste": "tooth paste",
                            "hairbrush": "hair brush",
                            "hairdryer": "hair dryer",
                            "sunglasses": "sun glasses",
                            "raincoat": "rain coat",
                            "snowflake": "snow flake",
                            "fireplace": "fire place",
                            "waterfall": "water fall",
                            "earthquake": "earth quake",
                            "thunderstorm": "thunder storm",
                            "rainbow": "rain bow",
                            "sunshine": "sun shine",
                            "moonshine": "moon shine",
                            "starlight": "star light",
                            "candlelight": "candle light",
                            "flashlight": "flash light",
                            "nightlight": "night light",
                            "daybreak": "day break",
                            "nightfall": "night fall",
                            "rainfall": "rain fall",
                            "snowfall": "snow fall",
                            "downpour": "down pour",
                            "upstairs": "up stairs",
                            "downstairs": "down stairs",
                            "inside": "in side",
                            "outside": "out side",
                            "alongside": "along side",
                            "underside": "under side",
                            "backside": "back side",
                            "frontside": "front side",
                            "leftside": "left side",
                            "rightside": "right side",
                            "topside": "top side",
                            "bottomside": "bottom side",
                            "bedtime": "bed time",
                            "lunchtime": "lunch time",
                            "dinnertime": "dinner time",
                            "breakfast": "break fast",
                            "afternoon": "after noon",
                            "midnight": "mid night",
                            "midday": "mid day",
                            "daytime": "day time",
                            "nighttime": "night time",
                            "lifetime": "life time",
                            "halftime": "half time",
                            "fulltime": "full time",
                            "parttime": "part time",
                            "overtime": "over time",
                            "anytime": "any time",
                            "sometime": "some time",
                            "everytime": "every time",
                            "nobody": "no body",
                            "somebody": "some body",
                            "anybody": "any body",
                            "everybody": "every body",
                            "yourself": "your self",
                            "myself": "my self",
                            "himself": "him self",
                            "herself": "her self",
                            "themselves": "them selves",
                            "ourselves": "our selves",
                            "itself": "it self",
                            "oneself": "one self",
                            "cannot": "can not"
                        }
                        
                        if word.lower() in compound_splits:
                            error_word = compound_splits[word.lower()]
                            # Preserve capitalization
                            if word[0].isupper():
                                parts = error_word.split()
                                parts[0] = parts[0][0].upper() + parts[0][1:]
                                error_word = " ".join(parts)
                        else:
                            # Just use the original word
                            error_word = word
                            error_index = -1  # Reset since we didn't make an error
                    elif error_type == "join" and i < len(words) - 1:
                        # Join this word with the next word (only if they make sense together)
                        next_word = words[i + 1]
                        combined = word + next_word
                        
                        # Only join if the combined word is not too long
                        if len(combined) <= 12:
                            error_word = word
                            # We'll handle the join when we get to the next word
                            # by skipping it
                        else:
                            # Just use the original word
                            error_word = word
                            error_index = -1  # Reset since we didn't make an error
                    else:
                        # Just use the original word
                        error_word = word
                        error_index = -1  # Reset since we didn't make an error
                    
                    # Type the error word
                    keyboard_client.type_text(ip, port, error_word)
                else:
                    # Type the word correctly
                    keyboard_client.type_text(ip, port, word)
                
                # Add space between words
                if i < len(words) - 1:
                    keyboard_client.type_text(ip, port, " ")
                
                # Pause between words with natural variation
                time.sleep(random.uniform(DICTATION_WORD_DELAY_RANGE[0], DICTATION_WORD_DELAY_RANGE[1]))
                
                # Decide if we'll correct a previous error
                if error_index >= 0 and i > error_index and random.random() < 0.8:
                    # Calculate how many characters to delete
                    chars_to_delete = len(words[error_index])
                    
                    # Add spaces and following words if needed
                    for j in range(error_index + 1, i + 1):
                        chars_to_delete += len(words[j]) + 1  # +1 for space
                    
                    # Pause before correction
                    time.sleep(random.uniform(0.5, 1.0))
                    
                    # Delete back to the error
                    keyboard_client.delete_text(ip, port, chars_to_delete)
                    time.sleep(random.uniform(0.2, 0.4))
                    
                    # Type the correct word
                    keyboard_client.type_text(ip, port, original_word)
                    
                    # Add a space
                    keyboard_client.type_text(ip, port, " ")
                    
                    # Now retype the deleted words
                    for j in range(error_index + 1, i + 1):
                        keyboard_client.type_text(ip, port, words[j])
                        
                        # Add space if not the last word
                        if j < i:
                            keyboard_client.type_text(ip, port, " ")
                    
                    # Reset error tracking
                    error_index = -1
                    original_word = None
            
            # Add period at end of sentence if it doesn't already have punctuation
            if not sentence.rstrip().endswith(('.', '!', '?')):
                keyboard_client.type_text(ip, port, ".")
            
            # Add space between sentences
            if sentence_idx < len(sentences) - 1:
                keyboard_client.type_text(ip, port, " ")
        
        return True
        
    except Exception as e:
        print(f"Error in _handle_dictation: {e}")
        return False

def _build_typing_sequence(text: str) -> List[Dict]:
    """
    Build a sequence for realistic typing with human-like patterns.
    
    Args:
        text: Text to type
        
    Returns:
        List of action dictionaries
    """
    sequence = []
    
    # Split text into words and spaces
    words = re.findall(r'\S+|\s+', text)
    
    # Track state for autocorrect failures
    wrong_autocorrect_word = None
    wrong_autocorrect_index = -1
    
    # Track if we're at the start of a sentence (for auto-capitalization)
    start_of_sentence = True
    
    for i, word in enumerate(words):
        # Handle spaces
        if word.isspace():
            sequence.append({
                "action": "type",
                "text": " ",
                "delay_after": random.uniform(0.05, 0.15)
            })
            continue
        
        # Check if we need to fix a previous wrong autocorrect
        if wrong_autocorrect_word is not None and i - wrong_autocorrect_index >= 2 and random.random() < 0.9:
            # Calculate how many characters to delete (including spaces)
            chars_to_delete = sum(len(words[j]) for j in range(wrong_autocorrect_index + 1, i + 1))
            
            # Add spaces between words
            chars_to_delete += (i - wrong_autocorrect_index)
            
            # Delete back to the error
            sequence.append({
                "action": "delete",
                "count": chars_to_delete,
                "delay_after": random.uniform(0.2, 0.4)
            })
            
            # Type the correct word
            sequence.append({
                "action": "type",
                "text": wrong_autocorrect_word,
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Add a space
            sequence.append({
                "action": "type",
                "text": " ",
                "delay_after": random.uniform(0.05, 0.15)
            })
            
            # Now retype the deleted words
            for j in range(wrong_autocorrect_index + 1, i + 1):
                sequence.append({
                    "action": "type",
                    "text": words[j],
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # Add space if not the last word
                if j < i:
                    sequence.append({
                        "action": "type",
                        "text": " ",
                        "delay_after": random.uniform(0.05, 0.15)
                    })
            
            # Reset wrong autocorrect tracking
            wrong_autocorrect_word = None
            wrong_autocorrect_index = -1
            
            # Continue with the next word
            continue
        
        # Decide if we'll make a typo for this word
        make_typo = random.random() < TYPO_PROBABILITY and len(word) > 1 and not any(c in word for c in "@#$%^&*()_+-=[]{}|;:'\",.<>/?\\")
        
        # Check if this is a common word that might be typed quickly
        is_common_word = word.lower() in COMMON_WORDS and len(word) <= 5
        
        if make_typo and not is_common_word:
            # Generate a typo
            typo = _generate_typo(word)
            
            # Type the typo character by character
            for j, char in enumerate(typo):
                # Determine typing speed based on character type
                if char.isalpha() and char.islower():
                    # Common lowercase letters
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char.isalpha() and char.isupper() and not start_of_sentence:
                    # Capital letters (except at start of sentence)
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * CAPITAL_LETTER_MODIFIER
                elif char.isalpha() and char.isupper() and start_of_sentence:
                    # First letter of sentence is auto-capitalized, no extra delay
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char.isdigit():
                    # Numbers
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char in ".,":
                    # Common punctuation
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char in "!@#$%^&*()_+-=[]{}|;:'\",<>/?\\":
                    # Special characters
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0] * SPECIAL_CHAR_MODIFIER[0], 
                                              TYPING_DELAY_RANGE[1] * SPECIAL_CHAR_MODIFIER[1])
                else:
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                
                # Add variation based on tap movement statistics
                movement_factor = random.normalvariate(1.0, 0.15)  # 15% variation based on movement
                adjusted_delay = base_delay * movement_factor
                
                # Add to sequence
                sequence.append({
                    "action": "type",
                    "text": char,
                    "delay_after": adjusted_delay
                })
            
            # Decide if autocorrect will fix the typo
            if random.random() < AUTOCORRECT_PROBABILITY:
                # Simulate autocorrect behavior
                sequence.append({
                    "action": "delay",
                    "duration": random.uniform(0.2, 0.4)  # Brief pause for autocorrect
                })
                
                # Delete the typo
                sequence.append({
                    "action": "delete",
                    "count": len(typo),
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # Get a replacement (sometimes wrong)
                replacement = _get_autocorrect_replacement(word, typo)
                
                # Type the replacement
                sequence.append({
                    "action": "type",
                    "text": replacement,
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # If the replacement is wrong, track it for potential later correction
                if replacement != word:
                    wrong_autocorrect_word = word
                    wrong_autocorrect_index = i
        else:
            # No typo, type the word normally
            for j, char in enumerate(word):
                # Determine typing speed based on character type
                if is_common_word:
                    # Burst typing for common words
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * BURST_TYPING_MODIFIER
                elif char.isalpha() and char.islower():
                    # Common lowercase letters
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char.isalpha() and char.isupper() and not start_of_sentence:
                    # Capital letters (except at start of sentence)
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * CAPITAL_LETTER_MODIFIER
                elif char.isalpha() and char.isupper() and start_of_sentence:
                    # First letter of sentence is auto-capitalized, no extra delay
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char.isdigit():
                    # Numbers
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char in ".,":
                    # Common punctuation
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char in "!@#$%^&*()_+-=[]{}|;:'\",<>/?\\":
                    # Special characters
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0] * SPECIAL_CHAR_MODIFIER[0], 
                                              TYPING_DELAY_RANGE[1] * SPECIAL_CHAR_MODIFIER[1])
                else:
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                
                # Add variation based on tap movement statistics
                movement_factor = random.normalvariate(1.0, 0.15)  # 15% variation based on movement
                adjusted_delay = base_delay * movement_factor
                
                # Add to sequence
                sequence.append({
                    "action": "type",
                    "text": char,
                    "delay_after": adjusted_delay
                })
        
        # Add a space after the word (unless it's the last word)
        if i < len(words) - 1 and not words[i+1].isspace():
            sequence.append({
                "action": "type",
                "text": " ",
                "delay_after": random.uniform(0.05, 0.15)
            })
        
        # Reset start_of_sentence flag
        start_of_sentence = word.endswith(('.', '!', '?'))
    
    # Ensure we fix any remaining wrong autocorrect at the end
    if wrong_autocorrect_word is not None:
        # Pause as if noticing the error
        sequence.append({
            "action": "delay",
            "duration": random.uniform(0.5, 1.0)
        })
        
        # Calculate how many characters to delete to get back to the error
        words_after_error = len(words) - wrong_autocorrect_index - 1
        chars_to_delete = 0
        
        # Count characters in words after the error
        for j in range(wrong_autocorrect_index + 1, len(words)):
            if not words[j].isspace():  # Skip spaces in the word list
                chars_to_delete += len(words[j])
        
        # Add spaces between words
        chars_to_delete += words_after_error - 1  # -1 because we're not counting the last space
        
        # If we have characters to delete
        if chars_to_delete > 0:
            # Delete back to the error word
            sequence.append({
                "action": "delete",
                "count": chars_to_delete,
                "delay_after": random.uniform(0.2, 0.4)
            })
        
        # Delete the wrong autocorrect word
        sequence.append({
            "action": "delete",
            "count": len(words[wrong_autocorrect_index]),
            "delay_after": random.uniform(0.1, 0.2)
        })
        
        # Type the correct word
        sequence.append({
            "action": "type",
            "text": wrong_autocorrect_word,
            "delay_after": random.uniform(0.1, 0.2)
        })
        
        # Add a space
        if words_after_error > 0:
            sequence.append({
                "action": "type",
                "text": " ",
                "delay_after": random.uniform(0.05, 0.15)
            })
        
        # Retype the remaining words
        for j in range(wrong_autocorrect_index + 1, len(words)):
            if not words[j].isspace():  # Skip spaces in the word list
                sequence.append({
                    "action": "type",
                    "text": words[j],
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # Add space if not the last word
                if j < len(words) - 1:
                    sequence.append({
                        "action": "type",
                        "text": " ",
                        "delay_after": random.uniform(0.05, 0.15)
                    })
    
    return sequence

def _build_dictation_sequence(text: str) -> List[Dict]:
    """
    Build a sequence for dictation-style typing.
    
    Args:
        text: Text to type
        
    Returns:
        List of action dictionaries
    """
    sequence = []
    
    # Split text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Track error state
    error_index = -1
    original_word = None
    
    for sentence_idx, sentence in enumerate(sentences):
        # Split sentence into words
        words = sentence.split()
        
        # Process each word
        for i, word in enumerate(words):
            # Check if we need to fix a previous error
            if error_index != -1 and i - error_index >= 2 and random.random() < 0.7:
                # Calculate how many characters to delete (including spaces)
                chars_to_delete = sum(len(words[j]) for j in range(error_index + 1, i + 1))
                
                # Add spaces between words
                chars_to_delete += (i - error_index)
                
                # Delete back to the error
                sequence.append({
                    "action": "delete",
                    "count": chars_to_delete,
                    "delay_after": random.uniform(0.2, 0.4)
                })
                
                # Type the correct word
                sequence.append({
                    "action": "type",
                    "text": original_word,
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # Add a space
                sequence.append({
                    "action": "type",
                    "text": " ",
                    "delay_after": random.uniform(0.05, 0.15)
                })
                
                # Now retype the deleted words
                for j in range(error_index + 1, i + 1):
                    sequence.append({
                        "action": "type",
                        "text": words[j],
                        "delay_after": random.uniform(0.1, 0.2)
                    })
                    
                    # Add space if not the last word
                    if j < i:
                        sequence.append({
                            "action": "type",
                            "text": " ",
                            "delay_after": random.uniform(0.05, 0.15)
                        })
                
                # Reset error tracking
                error_index = -1
                original_word = None
                
                # Continue with the next word
                continue
            
            # Decide if we'll make an error
            make_error = random.random() < 0.15 and len(word) > 2
            
            if make_error and word.lower() in COMMON_HOMOPHONES:
                # Use a homophone error
                error_word = random.choice(COMMON_HOMOPHONES[word.lower()])
                
                # Preserve capitalization
                if word[0].isupper():
                    error_word = error_word[0].upper() + error_word[1:]
                
                sequence.append({
                    "action": "type",
                    "text": error_word,
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # Track the error for potential correction
                error_index = i
                original_word = word
            elif make_error and len(word) > 4:
                # Make a plausible dictation error
                error_type = random.choice(["similar", "compound_split", "join"])
                
                if error_type == "similar":
                    # Similar sounding word
                    similar_words = {
                        "their": "there", "there": "their", "they're": "their",
                        "your": "you're", "you're": "your", "its": "it's", "it's": "its",
                        "affect": "effect", "effect": "affect", "then": "than", "than": "then",
                        "accept": "except", "except": "accept", "lose": "loose", "loose": "lose",
                        "weather": "whether", "whether": "weather", "to": "too", "too": "to",
                        "hear": "here", "here": "hear", "right": "write", "write": "right"
                    }
                    
                    if word.lower() in similar_words:
                        error_word = similar_words[word.lower()]
                        # Preserve capitalization
                        if word[0].isupper():
                            error_word = error_word[0].upper() + error_word[1:]
                            
                        sequence.append({
                            "action": "type",
                            "text": error_word,
                            "delay_after": random.uniform(0.1, 0.2)
                        })
                        
                        # Track the error for potential correction
                        error_index = i
                        original_word = word
                    else:
                        # Just type the word correctly
                        sequence.append({
                            "action": "type",
                            "text": word,
                            "delay_after": random.uniform(0.1, 0.2)
                        })
                elif error_type == "compound_split" and len(word) > 5:
                    # Only split at realistic compound word boundaries
                    compound_splits = {
                        "keyboard": "key board",
                        "notebook": "note book",
                        "background": "back ground",
                        "sometimes": "some times",
                        "everything": "every thing",
                        "something": "some thing",
                        "anything": "any thing",
                        "nothing": "no thing",
                        "downtown": "down town",
                        "bedroom": "bed room",
                        "bathroom": "bath room",
                        "classroom": "class room",
                        "football": "foot ball",
                        "baseball": "base ball",
                        "basketball": "basket ball",
                        "weekend": "week end",
                        "birthday": "birth day",
                        "sunlight": "sun light",
                        "moonlight": "moon light",
                        "daylight": "day light",
                        "software": "soft ware",
                        "hardware": "hard ware",
                        "firewall": "fire wall",
                        "network": "net work",
                        "website": "web site",
                        "homepage": "home page",
                        "username": "user name",
                        "password": "pass word",
                        "database": "data base",
                        "filename": "file name",
                        "keyboard": "key board",
                        "smartphone": "smart phone",
                        "headphone": "head phone",
                        "microphone": "micro phone",
                        "loudspeaker": "loud speaker",
                        "toothbrush": "tooth brush",
                        "toothpaste": "tooth paste",
                        "hairbrush": "hair brush",
                        "hairdryer": "hair dryer",
                        "sunglasses": "sun glasses",
                        "raincoat": "rain coat",
                        "snowflake": "snow flake",
                        "fireplace": "fire place",
                        "waterfall": "water fall",
                        "earthquake": "earth quake",
                        "thunderstorm": "thunder storm",
                        "rainbow": "rain bow",
                        "sunshine": "sun shine",
                        "moonshine": "moon shine",
                        "starlight": "star light",
                        "candlelight": "candle light",
                        "flashlight": "flash light",
                        "nightlight": "night light",
                        "daybreak": "day break",
                        "nightfall": "night fall",
                        "rainfall": "rain fall",
                        "snowfall": "snow fall",
                        "downpour": "down pour",
                        "upstairs": "up stairs",
                        "downstairs": "down stairs",
                        "inside": "in side",
                        "outside": "out side",
                        "alongside": "along side",
                        "underside": "under side",
                        "backside": "back side",
                        "frontside": "front side",
                        "leftside": "left side",
                        "rightside": "right side",
                        "topside": "top side",
                        "bottomside": "bottom side",
                        "bedtime": "bed time",
                        "lunchtime": "lunch time",
                        "dinnertime": "dinner time",
                        "breakfast": "break fast",
                        "afternoon": "after noon",
                        "midnight": "mid night",
                        "midday": "mid day",
                        "daytime": "day time",
                        "nighttime": "night time",
                        "lifetime": "life time",
                        "halftime": "half time",
                        "fulltime": "full time",
                        "parttime": "part time",
                        "overtime": "over time",
                        "anytime": "any time",
                        "sometime": "some time",
                        "everytime": "every time",
                        "nobody": "no body",
                        "somebody": "some body",
                        "anybody": "any body",
                        "everybody": "every body",
                        "yourself": "your self",
                        "myself": "my self",
                        "himself": "him self",
                        "herself": "her self",
                        "themselves": "them selves",
                        "ourselves": "our selves",
                        "itself": "it self",
                        "oneself": "one self",
                        "cannot": "can not"
                    }
                    
                    if word.lower() in compound_splits:
                        error_word = compound_splits[word.lower()]
                        # Preserve capitalization
                        if word[0].isupper():
                            parts = error_word.split()
                            parts[0] = parts[0][0].upper() + parts[0][1:]
                            error_word = " ".join(parts)
                            
                        sequence.append({
                            "action": "type",
                            "text": error_word,
                            "delay_after": random.uniform(0.1, 0.2)
                        })
                        
                        # Track the error for potential correction
                        error_index = i
                        original_word = word
                    else:
                        # Just type the word correctly
                        sequence.append({
                            "action": "type",
                            "text": word,
                            "delay_after": random.uniform(0.1, 0.2)
                        })
                else:
                    # Just type the word correctly
                    sequence.append({
                        "action": "type",
                        "text": word,
                        "delay_after": random.uniform(0.1, 0.2)
                    })
            
            # Add space between words
            if i < len(words) - 1:
                sequence.append({
                    "action": "type",
                    "text": " ",
                    "delay_after": random.uniform(0.05, 0.15)
                })
        
        # Add period at end of sentence if it doesn't already have punctuation
        if not sentence.rstrip().endswith(('.', '!', '?')):
            sequence.append({
                "action": "type",
                "text": ".",
                "delay_after": random.uniform(0.1, 0.2)
            })
        
        # Add space between sentences
        if sentence_idx < len(sentences) - 1:
            sequence.append({
                "action": "type",
                "text": " ",
                "delay_after": random.uniform(0.5, 1.0)
            })
    
    # Ensure we fix any remaining errors at the end
    if error_index != -1:
        # Go back to the error and fix it
        words_after_error = len(words) - error_index - 1
        chars_to_delete = sum(len(words[j]) for j in range(error_index, len(words)))
        chars_to_delete += words_after_error  # Add spaces
        
        sequence.append({
            "action": "delete",
            "count": chars_to_delete,
            "delay_after": random.uniform(0.2, 0.4)
        })
        
        # Type the correct word
        sequence.append({
            "action": "type",
            "text": original_word,
            "delay_after": random.uniform(0.1, 0.2)
        })
        
        # Add a space
        sequence.append({
            "action": "type",
            "text": " ",
            "delay_after": random.uniform(0.05, 0.15)
        })
        
        # Retype the remaining words
        for j in range(error_index + 1, len(words)):
            sequence.append({
                "action": "type",
                "text": words[j],
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Add space if not the last word
            if j < len(words) - 1:
                sequence.append({
                    "action": "type",
                    "text": " ",
                    "delay_after": random.uniform(0.05, 0.15)
                })
    
    return sequence

def _build_autofill_sequence(text: str) -> List[Dict]:
    """
    Build a sequence for autofill-style typing.
    
    Args:
        text: Text to type
        
    Returns:
        List of action dictionaries
    """
    sequence = []
    
    # Check if it's an email or URL
    if '@' in text or text.startswith(('http://', 'https://', 'www.')):
        # For emails and URLs, type a prefix and then use suggestion
        if '@' in text:
            # For email, type the part before @ and select suggestion
            prefix = text.split('@')[0]
            
            # Type the prefix character by character
            for char in prefix:
                sequence.append({
                    "action": "type",
                    "text": char,
                    "delay_after": random.uniform(0.1, 0.2)
                })
            
            # Pause as if looking at suggestions
            sequence.append({
                "action": "delay",
                "duration": random.uniform(0.5, 1.0)
            })
            
            # Simulate tapping on a suggestion (by typing the full text)
            sequence.append({
                "action": "type",
                "text": text,
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            return sequence
        
        # For common phrases
        words = text.split()
        
        if len(words) <= 3:
            # Type the first word
            sequence.append({
                "action": "type",
                "text": words[0],
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Pause to look at suggestions
            sequence.append({
                "action": "delay",
                "duration": random.uniform(0.3, 0.6)
            })
            
            # Delete what we typed (simulating selecting a suggestion)
            sequence.append({
                "action": "delete",
                "count": len(words[0]),
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Type the full phrase (as if selected from suggestions)
            sequence.append({
                "action": "type",
                "text": text,
                "delay_after": random.uniform(0.1, 0.2)
            })
        else:
            # For longer phrases, type first few words then use suggestion
            words_to_type = min(2, len(words) - 1)
            
            # Type the first few words
            for i in range(words_to_type):
                sequence.append({
                    "action": "type",
                    "text": words[i],
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                sequence.append({
                    "action": "type",
                    "text": " ",
                    "delay_after": random.uniform(0.05, 0.15)
                })
            
            # Type part of the next word
            partial_word = words[words_to_type][:min(3, len(words[words_to_type]))]
            sequence.append({
                "action": "type",
                "text": partial_word,
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Pause as if looking at suggestions
            sequence.append({
                "action": "delay",
                "duration": random.uniform(0.5, 1.0)
            })
            
            # Delete the partial word
            sequence.append({
                "action": "delete",
                "count": len(partial_word),
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Type the rest of the phrase (as if selected from suggestions)
            remaining_text = " ".join(words[words_to_type:])
            sequence.append({
                "action": "type",
                "text": remaining_text,
                "delay_after": random.uniform(0.1, 0.2)
            })
        
        return sequence
    
    # For other text, just use the typing sequence
    return _build_typing_sequence(text)

def _generate_typo(word: str) -> str:
    """
    Generate a realistic typo for a given word.
    
    Args:
        word: The original word
        
    Returns:
        A word with a typo
    """
    if len(word) <= 1:
        return word
    
    # Choose typo type
    typo_type = random.choices(
        ["swap", "double", "adjacent", "wrong_key", "missing", "extra"],
        weights=[0.25, 0.15, 0.25, 0.2, 0.1, 0.05],
        k=1
    )[0]
    
    # Create a copy of the word as a list for easier manipulation
    chars = list(word)
    
    if typo_type == "swap" and len(word) >= 3:
        # Swap two adjacent characters (common error)
        pos = random.randint(0, len(word) - 2)
        chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
    
    elif typo_type == "double" and len(word) >= 2:
        # Double a letter (common error)
        pos = random.randint(0, len(word) - 1)
        chars.insert(pos, chars[pos])
    
    elif typo_type == "adjacent" and len(word) >= 2:
        # Hit an adjacent key on the keyboard
        keyboard_adjacency = {
            'a': 'qwsz', 'b': 'vghn', 'c': 'xdfv', 'd': 'serfcx', 'e': 'wrsdf',
            'f': 'drtgvc', 'g': 'ftyhbv', 'h': 'gyujnb', 'i': 'ujklo', 'j': 'huikmn',
            'k': 'jiolm', 'l': 'kop', 'm': 'njk', 'n': 'bhjm', 'o': 'iklp',
            'p': 'ol', 'q': 'wa', 'r': 'edft', 's': 'awedxz', 't': 'rfgy',
            'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc', 'y': 'tghu',
            'z': 'asx'
        }
        
        pos = random.randint(0, len(word) - 1)
        char = word[pos].lower()
        
        if char in keyboard_adjacency:
            adjacent_keys = keyboard_adjacency[char]
            replacement = random.choice(adjacent_keys)
            
            # Preserve capitalization
            if word[pos].isupper():
                replacement = replacement.upper()
                
            chars[pos] = replacement
    
    elif typo_type == "wrong_key":
        # Just hit a random wrong key
        pos = random.randint(0, len(word) - 1)
        replacement = random.choice("abcdefghijklmnopqrstuvwxyz")
        
        # Preserve capitalization
        if word[pos].isupper():
            replacement = replacement.upper()
            
        chars[pos] = replacement
    
    elif typo_type == "missing" and len(word) >= 3:
        # Missing letter
        pos = random.randint(0, len(word) - 1)
        chars.pop(pos)
    
    else:  # extra
        # Extra letter
        pos = random.randint(0, len(word))
        chars.insert(pos, random.choice("abcdefghijklmnopqrstuvwxyz"))
    
    return ''.join(chars)

def _get_autocorrect_replacement(original_word: str, typo: str) -> str:
    """
    Simulate realistic autocorrect behavior by providing a replacement for a typo.
    
    Args:
        original_word: The original intended word
        typo: The typo that was typed
        
    Returns:
        Either the correct word (95% chance) or a plausible but wrong correctly-spelled
        word (5% chance). Never returns a misspelled word.
    """
    # 95% chance of correct autocorrect
    if random.random() < 0.95:
        return original_word
    
    # 5% chance of wrong but correctly spelled word
    # Check if the original word has a common confusion pair
    if original_word.lower() in AUTOCORRECT_FAILS:
        wrong_word = AUTOCORRECT_FAILS[original_word.lower()]
        
        # Preserve capitalization
        if original_word[0].isupper():
            wrong_word = wrong_word[0].upper() + wrong_word[1:]
            
        return wrong_word
    
    # If no confusion pair exists, just return the correct word
    return original_word

# Import subprocess here to avoid circular imports
import subprocess

if __name__ == "__main__":
    # Test code
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python type.py <device_id> <text>")
        sys.exit(1)
    
    device_id = sys.argv[1]
    text = " ".join(sys.argv[2:])
    
    # Default region for testing
    region = [100, 300, 400, 400]
    
    result = type_text(device_id, region, text)
    print(f"Typing result: {result}")
```
## keyboard_client.py
```python
import requests
import json
import time
import random
import argparse

def send_command(ip, port, command_dict):
    """Send a command to the keyboard."""
    try:
        response = requests.post(f"http://{ip}:{port}/command", 
                                json=command_dict, 
                                timeout=30)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}

def type_text(ip, port, text):
    """Type text with the keyboard."""
    return send_command(ip, port, {"action": "type", "text": text})

def delete_text(ip, port, count=1):
    """Delete the specified number of characters."""
    return send_command(ip, port, {"action": "delete", "count": count})

def update_status(ip, port, message):
    """Update the status message in the speech bubble."""
    return send_command(ip, port, {"action": "status", "message": message})

def set_cursor_position(ip, port, position):
    """Move the cursor to the specified position."""
    return send_command(ip, port, {"action": "cursor", "position": position})

def select_text(ip, port, start, end):
    """Select text from start to end position."""
    return send_command(ip, port, {"action": "select", "start": start, "end": end})

def select_all(ip, port):
    """Select all text in the current field."""
    return send_command(ip, port, {"action": "select_all"})

def get_clipboard(ip, port):
    """Get the current clipboard content."""
    response = send_command(ip, port, {"action": "clipboard_get"})
    if response.get("status") == "success" and "text" in response:
        return response["text"].get("text", "")
    return ""

def set_clipboard(ip, port, text):
    """Set the clipboard content."""
    return send_command(ip, port, {"action": "clipboard_set", "text": text})

def cut_text(ip, port):
    """Cut the selected text."""
    return send_command(ip, port, {"action": "cut"})

def copy_text(ip, port):
    """Copy the selected text."""
    return send_command(ip, port, {"action": "copy"})

def paste_text(ip, port):
    """Paste text from clipboard."""
    return send_command(ip, port, {"action": "paste"})

def execute_sequence(ip, port, sequence):
    """Execute a full sequence of typing actions.
    
    Args:
        ip: IP address of the keyboard server
        port: Port of the keyboard server
        sequence: List of action dictionaries, each containing:
                 - action: The action to perform (type, delete, cursor, etc.)
                 - Additional parameters specific to the action
                 - delay_after: Delay in seconds after this action
    
    Returns:
        Response from the server
    """
    return send_command(ip, port, {"action": "execute_sequence", "sequence": sequence})

def demo_mode(ip, port):
    """Run a demo of the keyboard's capabilities."""
    # Connect and show status
    print("Running demo mode...")
    update_status(ip, port, "Connected!")
    time.sleep(1)
    
    # Type some text naturally
    print("Typing naturally...")
    update_status(ip, port, "Typing naturally...")
    type_text(ip, port, "Hello, I'm typing naturally!")
    time.sleep(1)
    
    # Delete some text
    print("Deleting text...")
    update_status(ip, port, "Deleting text...")
    delete_text(ip, port, 5)
    time.sleep(1)
    
    # Type with voice simulation
    print("Voice typing...")
    update_status(ip, port, "Voice typing...")
    type_text(ip, port, "This is how voice typing would look like.")
    time.sleep(1)
    
    # Demonstrate cursor positioning
    print("Cursor positioning...")
    update_status(ip, port, "Moving cursor...")
    set_cursor_position(ip, port, 5)
    time.sleep(0.5)
    type_text(ip, port, "INSERTED ")
    time.sleep(1)
    
    # Demonstrate clipboard operations
    print("Clipboard operations...")
    update_status(ip, port, "Clipboard demo...")
    select_all(ip, port)
    time.sleep(0.5)
    copy_text(ip, port)
    time.sleep(0.5)
    set_cursor_position(ip, port, 0)
    time.sleep(0.5)
    paste_text(ip, port)
    
    # Done
    print("Demo completed!")
    update_status(ip, port, "Finished demo!")

def interactive_mode(ip, port):
    """Run an interactive session with the keyboard."""
    print(f"Connected to keyboard at {ip}:{port}")
    print("Type commands in the format: action:text")
    print("Available actions: type, delete, status, cursor, select, clipboard_get, clipboard_set, select_all, cut, copy, paste, exit")
    print("Examples:")
    print("  type:Hello, world!")
    print("  delete:5")
    print("  status:I'm thinking...")
    print("  cursor:10")
    print("  select:5,10")
    print("  clipboard_get")
    print("  clipboard_set:New clipboard text")
    print("  select_all")
    print("  cut")
    print("  copy")
    print("  paste")
    print("  exit")
    
    update_status(ip, port, "Interactive mode")
    
    while True:
        command = input("> ")
        if command.lower() == "exit":
            update_status(ip, port, "Disconnected")
            break
            
        parts = command.split(":", 1)
        
        if len(parts) == 1:
            action = parts[0]
            if action == "clipboard_get":
                clipboard_text = get_clipboard(ip, port)
                print(f"Clipboard content: {clipboard_text}")
            elif action == "select_all":
                response = select_all(ip, port)
                print(f"Response: {response}")
            elif action == "cut":
                response = cut_text(ip, port)
                print(f"Response: {response}")
            elif action == "copy":
                response = copy_text(ip, port)
                print(f"Response: {response}")
            elif action == "paste":
                response = paste_text(ip, port)
                print(f"Response: {response}")
            else:
                print("Invalid command format. Use action:text or action")
            continue
            
        action, text = parts
        
        if action == "type":
            response = type_text(ip, port, text)
            print(f"Response: {response}")
        elif action == "delete":
            try:
                count = int(text)
                response = delete_text(ip, port, count)
                print(f"Response: {response}")
            except ValueError:
                print("Delete count must be a number")
        elif action == "status":
            response = update_status(ip, port, text)
            print(f"Response: {response}")
        elif action == "cursor":
            try:
                position = int(text)
                response = set_cursor_position(ip, port, position)
                print(f"Response: {response}")
            except ValueError:
                print("Cursor position must be a number")
        elif action == "select":
            try:
                start, end = map(int, text.split(","))
                response = select_text(ip, port, start, end)
                print(f"Response: {response}")
            except (ValueError, IndexError):
                print("Select requires two numbers separated by comma (start,end)")
        elif action == "clipboard_set":
            response = set_clipboard(ip, port, text)
            print(f"Response: {response}")
        else:
            print(f"Unknown action: {action}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SociaLlama Keyboard Client")
    parser.add_argument("--ip", default="192.168.1.100", help="IP address of the keyboard")
    parser.add_argument("--port", default=8080, type=int, help="Port of the keyboard server")
    parser.add_argument("--demo", action="store_true", help="Run demo mode")
    parser.add_argument("--type", help="Type the specified text")
    parser.add_argument("--delete", type=int, help="Delete the specified number of characters")
    parser.add_argument("--status", help="Update the status message")
    parser.add_argument("--cursor", type=int, help="Set cursor position")
    parser.add_argument("--select", help="Select text (format: start,end)")
    parser.add_argument("--clipboard-get", action="store_true", help="Get clipboard content")
    parser.add_argument("--clipboard-set", help="Set clipboard content")
    parser.add_argument("--select-all", action="store_true", help="Select all text")
    parser.add_argument("--cut", action="store_true", help="Cut selected text")
    parser.add_argument("--copy", action="store_true", help="Copy selected text")
    parser.add_argument("--paste", action="store_true", help="Paste text from clipboard")
    
    args = parser.parse_args()
    
    # Process commands
    if args.demo:
        demo_mode(args.ip, args.port)
    elif args.type:
        response = type_text(args.ip, args.port, args.type)
        print(f"Response: {response}")
    elif args.delete:
        response = delete_text(args.ip, args.port, args.delete)
        print(f"Response: {response}")
    elif args.status:
        response = update_status(args.ip, args.port, args.status)
        print(f"Response: {response}")
    elif args.cursor is not None:
        response = set_cursor_position(args.ip, args.port, args.cursor)
        print(f"Response: {response}")
    elif args.select:
        try:
            start, end = map(int, args.select.split(","))
            response = select_text(args.ip, args.port, start, end)
            print(f"Response: {response}")
        except (ValueError, IndexError):
            print("Select requires two numbers separated by comma (start,end)")
    elif args.clipboard_get:
        clipboard_text = get_clipboard(args.ip, args.port)
        print(f"Clipboard content: {clipboard_text}")
    elif args.clipboard_set:
        response = set_clipboard(args.ip, args.port, args.clipboard_set)
        print(f"Response: {response}")
    elif args.select_all:
        response = select_all(args.ip, args.port)
        print(f"Response: {response}")
    elif args.cut:
        response = cut_text(args.ip, args.port)
        print(f"Response: {response}")
    elif args.copy:
        response = copy_text(args.ip, args.port)
        print(f"Response: {response}")
    elif args.paste:
        response = paste_text(args.ip, args.port)
        print(f"Response: {response}")
    else:
        interactive_mode(args.ip, args.port)
```
