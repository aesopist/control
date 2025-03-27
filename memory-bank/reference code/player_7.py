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
