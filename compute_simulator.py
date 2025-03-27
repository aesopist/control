#!/usr/bin/env python
"""
Compute Simulator for testing Control component.
Simulates the Cloud relay by creating a WebSocket server that Control can connect to.
"""

import asyncio
import json
import logging
import websockets
import argparse
import uuid
import time
import os
from pathlib import Path
import struct
from typing import Dict, Any, Optional, List, Tuple
import base64
from datetime import datetime

# Configure logging
log_dir = Path("logs/compute_simulator")
log_dir.mkdir(parents=True, exist_ok=True)

current_time = datetime.now()
log_file = log_dir / f"{current_time.strftime('%B_%d_%Y_%H%M')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file)
    ]
)

logger = logging.getLogger("ComputeSimulator")
logger.info(f"Logging to file: {log_file}")

# Client connections
clients = {}
device_statuses = {}

# Binary message handling
HEADER_FORMAT = "!III"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def create_binary_message(package_id: str, content_id: str, data: bytes) -> bytes:
    """Create binary message with header"""
    package_id_int = string_to_int(package_id)
    content_id_int = string_to_int(content_id)
    
    header = struct.pack(
        HEADER_FORMAT,
        package_id_int,
        content_id_int,
        len(data)
    )
    
    return header + data

def string_to_int(s: str) -> int:
    """Convert string to integer hash"""
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    return h

# Sample workflow data
def create_sample_workflow(device_id: str) -> Dict[str, Any]:
    """Create a sample workflow package"""
    workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
    
    return {
        "package_type": "workflow",
        "package_id": f"package_{uuid.uuid4().hex[:8]}",
        "workflow": {
            "workflow_id": workflow_id,
            "name": "Test Workflow",
            "sequences": [
                {
                    "sequence_id": f"sequence_{uuid.uuid4().hex[:8]}",
                    "name": "Test Sequence",
                    "steps": [
                        {
                            "step_id": f"step_{uuid.uuid4().hex[:8]}",
                            "type": "tap",
                            "coordinates": [540, 960],
                            "expected_screen_after": "screen_id_1"
                        }
                    ]
                }
            ]
        },
        "screen_registry": {
            "screen_id_1": {
                "name": "Home Screen",
                "image": "screen_id_1.png",
                "validation_regions": [
                    {"x1": 100, "y1": 200, "x2": 300, "y2": 400}
                ]
            }
        },
        "device_id": device_id
    }

def create_live_command(device_id: str, command_type: str = "tap", 
                       coordinates: List[int] = [540, 960]) -> Dict[str, Any]:
    """Create a live command package"""
    return {
        "package_type": "live_command",
        "package_id": f"package_{uuid.uuid4().hex[:8]}",
        "command": {
            "command_id": f"command_{uuid.uuid4().hex[:8]}",
            "type": command_type,
            "coordinates": coordinates,
            "verify_screen": False,
            "return_screenshot": True
        },
        "device_id": device_id,
        "session_id": f"session_{uuid.uuid4().hex[:8]}",
        "timestamp": str(time.time())
    }

def create_special_sequence(device_id: str) -> Dict[str, Any]:
    """Create a special sequence package"""
    return {
        "package_type": "special_sequence",
        "package_id": f"package_{uuid.uuid4().hex[:8]}",
        "sequence": {
            "sequence_id": f"sequence_{uuid.uuid4().hex[:8]}",
            "name": "Test Special Sequence",
            "code": """
import time
import sys
import os

def main():
    device_id = os.environ.get('CONTROL_DEVICE_ID')
    workflow_id = os.environ.get('CONTROL_WORKFLOW_ID')
    
    print(f"Running special sequence for device {device_id} in workflow {workflow_id}")
    time.sleep(2)  # Simulate work
    
    # Return success with some data
    result = {
        "status": "success",
        "data": {
            "message": "Special sequence executed successfully",
            "timestamp": time.time()
        }
    }
    
    return result

# Set the result to be returned
result = main()
""",
            "parameters": {
                "param1": "value1",
                "param2": "value2"
            }
        },
        "device_id": device_id,
        "timestamp": str(time.time())
    }

async def handle_client_messages(websocket, path):
    """Handle messages from Control client"""
    client_id = None
    
    try:
        # Get client ID from query params
        if "?" in path:
            query = path.split("?")[1]
            params = dict(p.split("=") for p in query.split("&"))
            client_id = params.get("client_id", f"unknown_{uuid.uuid4().hex[:8]}")
        else:
            client_id = f"unknown_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"New client connected: {client_id}")
        clients[client_id] = websocket
        
        # Listen for messages from client
        async for message in websocket:
            try:
                # Check if binary message
                if isinstance(message, bytes):
                    logger.debug(f"Received binary message from {client_id}: {message[:50]}...")
                    await handle_binary_message(websocket, message)
                    continue
                
                # Parse JSON message
                msg_data = json.loads(message)
                msg_type = msg_data.get("type")
                logger.debug(f"Received JSON message from {client_id}: {msg_data}")
                
                # Handle message based on type
                if msg_type == "ping":
                    response = {"type": "pong", "data": {}}
                    await websocket.send(json.dumps(response))
                    logger.debug(f"Sent to {client_id}: {response}")
                elif msg_type == "status":
                    device_id = msg_data.get("device_id")
                    if device_id:
                        status = msg_data.get("data", {}).get("status")
                        if status:
                            device_statuses[device_id] = status
                            logger.info(f"Device {device_id} status: {status}")
                elif msg_type == "error":
                    logger.error(f"Error from client: {msg_data.get('data')}")
                elif msg_type == "result":
                    logger.info(f"Result from client: {msg_data.get('data')}")
                else:
                    logger.info(f"Received message of type {msg_type}: {msg_data}")
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse message: {message}")
            except Exception as e:
                logger.error(f"Error handling message: {e}")
    
    except Exception as e:
        logger.error(f"Connection error: {e}")
    
    finally:
        # Clean up on disconnect
        if client_id and client_id in clients:
            del clients[client_id]
        logger.info(f"Client {client_id} disconnected")

async def handle_binary_message(websocket, data: bytes):
    """Handle binary message from client"""
    try:
        # Parse header
        if len(data) < HEADER_SIZE:
            logger.error("Binary message too small for header")
            return
        
        header = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
        package_id_int, content_id_int, content_length = header
        
        # Extract content
        content = data[HEADER_SIZE:]
        
        # Verify content length
        if len(content) != content_length:
            logger.error(f"Content length mismatch: {len(content)} != {content_length}")
            return
        
        # Log receipt of binary data
        logger.info(f"Received binary data: package_id={package_id_int}, content_id={content_id_int}, length={content_length}")
        
        # If content is a PNG (screenshot), save it
        if content.startswith(b'\x89PNG'):
            # Create screenshots directory
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            # Save screenshot
            timestamp = int(time.time())
            screenshot_path = screenshots_dir / f"screenshot_{timestamp}.png"
            with open(screenshot_path, "wb") as f:
                f.write(content)
            logger.info(f"Saved screenshot: {screenshot_path}")
    
    except Exception as e:
        logger.error(f"Error handling binary message: {e}")

async def send_workflow(device_id: str):
    """Send a workflow package to Control"""
    if not clients:
        logger.error("No clients connected")
        return
    
    client_socket = next(iter(clients.values()))
    
    try:
        # Create workflow package
        workflow = create_sample_workflow(device_id)
        
        # Send to client
        await client_socket.send(json.dumps({
            "type": "workflow",
            "data": {
                "action": "start",
                "workflow_id": workflow["workflow"]["workflow_id"],
                **workflow
            }
        }))
        
        logger.info(f"Sent workflow package to device {device_id}")
        
        # Send reference image for screen verification
        # This would be a PNG file in a real system
        # Here we'll create a simple test image
        from PIL import Image, ImageDraw
        
        # Create a test image
        img = Image.new('RGB', (1080, 1920), color='white')
        draw = ImageDraw.Draw(img)
        draw.rectangle([100, 200, 300, 400], fill='blue')
        
        # Save to temp file
        img_path = Path("temp")
        img_path.mkdir(exist_ok=True)
        
        temp_img_path = img_path / "screen_id_1.png"
        img.save(temp_img_path)
        
        # Read image data
        with open(temp_img_path, "rb") as f:
            img_data = f.read()
        
        # Send as binary
        binary_msg = create_binary_message(
            workflow["package_id"],
            "screen_id_1.png",
            img_data
        )
        
        await client_socket.send(binary_msg)
        logger.info(f"Sent reference image for workflow")
        
        return workflow["workflow"]["workflow_id"]
        
    except Exception as e:
        logger.error(f"Error sending workflow: {e}")
        return None

async def send_live_command(device_id: str, command_type: str = "tap", 
                           coordinates: List[int] = [540, 960]):
    """Send a live command to Control"""
    if not clients:
        logger.error("No clients connected")
        return
    
    client_socket = next(iter(clients.values()))
    
    try:
        # Create command package
        command = create_live_command(device_id, command_type, coordinates)
        
        # Log the full command JSON
        logger.debug(f"Full command JSON: {json.dumps(command, indent=2)}")
        
        # Create the message to send
        message = {
            "type": "live_command",
            "data": command
        }
        
        # Log the full message
        logger.debug(f"Sending full message: {json.dumps(message, indent=2)}")
        
        # Send to client
        await client_socket.send(json.dumps(message))
        
        logger.info(f"Sent {command_type} command to device {device_id}")
        
        return command["command"]["command_id"]
        
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        return None

async def send_special_sequence(device_id: str):
    """Send a special sequence to Control"""
    if not clients:
        logger.error("No clients connected")
        return
    
    client_socket = next(iter(clients.values()))
    
    try:
        # Create special sequence package
        sequence = create_special_sequence(device_id)
        
        # Send to client
        await client_socket.send(json.dumps({
            "type": "special_sequence",
            "data": sequence
        }))
        
        logger.info(f"Sent special sequence to device {device_id}")
        
        return sequence["sequence"]["sequence_id"]
        
    except Exception as e:
        logger.error(f"Error sending special sequence: {e}")
        return None

async def interactive_console():
    """Interactive console for sending commands"""
    while True:
        print("\nCommands:")
        print("1. Send workflow")
        print("2. Send live command")
        print("3. Send special sequence")
        print("4. List connected clients")
        print("5. List device statuses")
        print("6. Exit")
        
        choice = await asyncio.get_event_loop().run_in_executor(
            None, lambda: input("Enter choice: ")
        )
        
        if choice == "1":
            device_id = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Enter device ID: ")
            )
            print(f"Sending workflow to device {device_id}")
            logger.debug(f"Sending workflow to device {device_id}")
            await send_workflow(device_id)
            
        elif choice == "2":
            device_id = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Enter device ID: ")
            )
            command_type = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Enter command type (tap, swipe, text): ")
            )
            
            if command_type == "tap":
                x = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: int(input("Enter x coordinate: "))
                )
                y = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: int(input("Enter y coordinate: "))
                )
                print(f"Sending tap command to device {device_id} at coordinates ({x}, {y})")
                logger.debug(f"Sending tap command to device {device_id} at coordinates ({x}, {y})")
                await send_live_command(device_id, "tap", [x, y])
                
            elif command_type == "swipe":
                start_x = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: int(input("Enter start x coordinate: "))
                )
                start_y = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: int(input("Enter start y coordinate: "))
                )
                end_x = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: int(input("Enter end x coordinate: "))
                )
                end_y = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: int(input("Enter end y coordinate: "))
                )
                
                command = create_live_command(device_id, "swipe", [])
                command["command"]["start_coordinates"] = [start_x, start_y]
                command["command"]["end_coordinates"] = [end_x, end_y]
                
                if clients:
                    client_socket = next(iter(clients.values()))
                
                # Log the full command JSON
                logger.debug(f"Full swipe command JSON: {json.dumps(command, indent=2)}")

                message = {
                    "type": "live_command",
                    "data": command
                }
                    
                # Log the full message
                logger.debug(f"Sending full message: {json.dumps(message, indent=2)}")

                print(f"Sending swipe command to device {device_id} from ({start_x}, {start_y}) to ({end_x}, {end_y})")
                logger.debug(f"Sending swipe command to device {device_id} from ({start_x}, {start_y}) to ({end_x}, {end_y})")
                await client_socket.send(json.dumps(message))
                logger.info(f"Sent swipe command to device {device_id}")
                
            elif command_type == "text":
                text = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("Enter text: ")
                )
                
                command = create_live_command(device_id, "text", [])
                command["command"]["keyboard_sequence"] = {
                    "sequence": [
                        {"action": "type", "text": text, "delay_after": 0.2}
                    ]
                }
                
                if clients:
                    client_socket = next(iter(clients.values()))
                
                # Log the full command JSON
                logger.debug(f"Full text command JSON: {json.dumps(command, indent=2)}")

                message = {
                    "type": "live_command",
                    "data": command
                }

                # Log the full message
                logger.debug(f"Sending full message: {json.dumps(message, indent=2)}")

                print(f"Sending text command to device {device_id} with text: {text}")
                logger.debug(f"Sending text command to device {device_id} with text: {text}")
                await client_socket.send(json.dumps(message))
                logger.info(f"Sent text command to device {device_id}")
            
        elif choice == "3":
            device_id = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Enter device ID: ")
            )
            print(f"Sending special sequence to device {device_id}")
            logger.debug(f"Sending special sequence to device {device_id}")
            await send_special_sequence(device_id)
            
        elif choice == "4":
            print("Connected clients:")
            for client_id, _ in clients.items():
                print(f"  - {client_id}")
                
        elif choice == "5":
            print("Device statuses:")
            for device_id, status in device_statuses.items():
                print(f"  - {device_id}: {status}")
                
        elif choice == "6":
            print("Exiting...")
            return
            
        else:
            print("Invalid choice")

async def main(host: str, port: int):
    """Main function"""
    # Start server
    server = await websockets.serve(handle_client_messages, host, port)
    logger.info(f"Server running at ws://{host}:{port}")
    
    # Start interactive console
    console_task = asyncio.create_task(interactive_console())
    
    # Run forever
    try:
        await console_task
    finally:
        server.close()
        await server.wait_closed()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute Simulator for Control testing")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind server to")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind server to")
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Server stopped")
