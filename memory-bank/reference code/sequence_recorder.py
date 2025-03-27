import subprocess
import time
import json
import threading
import queue
import keyboard
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime

class SequenceRecorder:
    """Records complete interaction sequences including events and screenshots"""
    
    # Known working scaling factors for S21
    X_FACTOR = 0.2637
    Y_FACTOR = 0.5859
    
    def __init__(self, device_id: str, base_path: Path):
        self.device_id = device_id
        self.base_path = base_path
        self.adb_path = base_path / "platform-tools" / "adb.exe"
        
        # Recording state
        self.is_recording = False
        self.is_paused = False
        self.sequence_start_time = None
        self.screen_count = 0
        self.current_session = None
        self.next_is_swipe = False  # Flag for swipe hotkey
        
        # Event tracking
        self.event_queue = queue.Queue()
        self.event_thread = None
        
        # Configure swipe hotkey
        keyboard.on_press(lambda e: self._mark_next_swipe() 
                         if keyboard.is_pressed('ctrl') and e.name == 'w' else None)
        
        # Sequence data
        self.sequence_data = {
            "events": [],
            "screenshots": [],
            "clipboard_commands": [],
            "special_sequences": []
        }
        
    def add_event(self, event: dict):
        """Add an event to the sequence data"""
        self.sequence_data["events"].append(event)

    def show_available_commands(self):
        """Show reminder of available commands"""
        print("\nAvailable commands:")
        print("Ctrl+S - Insert special sequence")
        print("Ctrl+T - Insert clipboard command")
        print("Ctrl+W - Mark next interaction as swipe")
        print("Ctrl+C - End recording")

    def _mark_next_swipe(self):
        """Mark next interaction as a swipe"""
        if self.is_recording and not self.is_paused:
            self.next_is_swipe = True
            print("\nNext interaction will be recorded as a swipe")

    def start_recording(self, session_path: Path) -> bool:
        """Start recording a new sequence"""
        try:
            self.current_session = session_path
            self.sequence_start_time = time.time()
            self.is_recording = True
            
            # Start event recording thread
            self.event_thread = threading.Thread(target=self._record_events)
            self.event_thread.daemon = True
            self.event_thread.start()
            
            # Take initial screenshot
            self.capture_screenshot("Initial state")
            
            print("\nRecording started...")
            return True
        except Exception as e:
            print(f"Failed to start recording: {str(e)}")
            return False

    def _record_events(self):
        """Record touch events from device"""
        try:
            process = subprocess.Popen(
                [str(self.adb_path), "-s", self.device_id, "shell", "getevent -lt /dev/input/event8"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            x = y = None
            tracking = False
            down_time = None
            
            while self.is_recording:
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                    
                line = process.stdout.readline().strip()
                if not line:
                    continue
                
                if "ABS_MT_POSITION_X" in line:
                    try:
                        x = int(line.split()[-1], 16)
                    except ValueError:
                        continue
                elif "ABS_MT_POSITION_Y" in line:
                    try:
                        y = int(line.split()[-1], 16)
                    except ValueError:
                        continue
                elif "BTN_TOUCH" in line:
                    if "DOWN" in line:
                        tracking = True
                        down_time = time.time()
                    elif "UP" in line and tracking:
                        if x is not None and y is not None:
                            # Apply scaling to coordinates
                            screen_x = int(x * self.X_FACTOR)
                            screen_y = int(y * self.Y_FACTOR)
                            up_time = time.time()
                            
                            # Create event based on whether it was marked as swipe
                            if self.next_is_swipe:
                                event = {
                                    "type": "swipe",
                                    "coordinates": {
                                        "start": None,  # To be filled in post-processing
                                        "end": [screen_x, screen_y]
                                    },
                                    "duration": up_time - down_time
                                }
                                self.next_is_swipe = False
                                print("\nSwipe recorded!")
                                self.show_available_commands()
                            else:
                                event = {
                                    "type": "tap",
                                    "coordinates": [screen_x, screen_y],
                                    "duration": up_time - down_time
                                }
                            
                            # Add event with timing
                            event["timestamp"] = datetime.now().strftime("%H:%M:%S")
                            self.sequence_data["events"].append(event)
                            
                            # Capture verification screenshot
                            if not self.is_paused:
                                time.sleep(1)  # Let UI settle
                                self.capture_screenshot(f"After {event['type']}")
                            
                        tracking = False
                        down_time = None
            
            process.terminate()
            
        except Exception as e:
            print(f"Event recording error: {str(e)}")

    def pause_recording(self):
        """Pause recording for special sequence"""
        self.is_paused = True

    def resume_recording(self):
        """Resume recording after special sequence"""
        self.is_paused = False
        print("\nRecording resumed!")
        self.show_available_commands()

    def add_clipboard_command(self, raw_text: str, field_reference: str):
        """Add clipboard command to sequence"""
        command = {
            "raw_text": raw_text,
            "field_reference": field_reference,
            "timestamp": time.time() - self.sequence_start_time
        }
        self.sequence_data["clipboard_commands"].append(command)
        print(f"\nCopied to clipboard: {field_reference}")
        self.show_available_commands()

    def add_special_sequence(self, description: str, verification_screen: str):
        """Add special sequence marker to recording"""
        sequence = {
            "description": description,
            "verification_screen": verification_screen,
            "timestamp": time.time() - self.sequence_start_time
        }
        self.sequence_data["special_sequences"].append(sequence)
        print("\nSpecial sequence recorded!")
        self.show_available_commands()

    def capture_screenshot(self, name: str) -> Optional[str]:
        """Capture and save verification screenshot"""
        try:
            self.screen_count += 1
            screenshot_path = self.current_session / f"screen{self.screen_count}.png"
            
            result = subprocess.run(
                [str(self.adb_path), "-s", self.device_id, "exec-out", "screencap -p"],
                capture_output=True
            )
            
            if result.returncode != 0:
                return None
            
            screenshot_path.write_bytes(result.stdout)
            self.sequence_data["screenshots"].append({
                "path": str(screenshot_path),
                "name": name,
                "number": self.screen_count
            })
            
            return str(screenshot_path)
            
        except Exception as e:
            print(f"Screenshot failed: {str(e)}")
            return None

    def execute_command(self, command: List[str]) -> Tuple[bool, str]:
        """Execute ADB command"""
        try:
            full_command = [str(self.adb_path), "-s", self.device_id] + command
            result = subprocess.run(full_command, capture_output=True, text=True)
            return result.returncode == 0, result.stdout
        except Exception as e:
            return False, str(e)

    def stop_recording(self) -> Dict:
        """Stop recording and return sequence data"""
        self.is_recording = False
        if self.event_thread:
            self.event_thread.join(timeout=1)
        
        return self.sequence_data
