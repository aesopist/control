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
