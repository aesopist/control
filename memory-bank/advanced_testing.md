# Advanced Testing Scenarios for Control

This guide provides examples of how to modify the Compute Simulator to test edge cases and error handling in the Control component.

## Testing Error Handling

### 1. Malformed Workflow Package

Add this function to the simulator and call it from the interactive console:

```python
async def send_malformed_workflow(device_id: str):
    """Send a malformed workflow package to test error handling"""
    if not clients:
        logger.error("No clients connected")
        return
    
    client_socket = next(iter(clients.values()))
    
    try:
        # Create deliberately malformed workflow package
        malformed = {
            "package_type": "workflow",
            "package_id": f"package_{uuid.uuid4().hex[:8]}",
            "workflow": {
                "workflow_id": f"workflow_{uuid.uuid4().hex[:8]}",
                "name": "Malformed Workflow",
                # Missing sequences key
                "steps": [  # Steps directly in workflow, not in a sequence
                    {
                        "step_id": f"step_{uuid.uuid4().hex[:8]}",
                        "type": "tap",
                        "coordinates": [540, 960]
                    }
                ]
            },
            "device_id": device_id
        }
        
        # Send to client
        await client_socket.send(json.dumps({
            "type": "workflow",
            "data": {
                "action": "start",
                "workflow_id": malformed["workflow"]["workflow_id"],
                **malformed
            }
        }))
        
        logger.info(f"Sent malformed workflow package to device {device_id}")
        
    except Exception as e:
        logger.error(f"Error sending malformed workflow: {e}")
```

### 2. Invalid Device ID

Test how Control handles requests for non-existent devices:

```python
async def send_to_invalid_device():
    """Send a command to a non-existent device"""
    invalid_device_id = "INVALID_DEVICE_ID_12345"
    await send_live_command(invalid_device_id, "tap", [540, 960])
```

### 3. Connection Interruption

Simulate a connection drop to test Control's reconnection logic:

```python
async def simulate_connection_drop():
    """Simulate a connection drop by closing all WebSockets"""
    if not clients:
        logger.error("No clients connected")
        return
    
    logger.info("Simulating connection drop...")
    
    # Close all connections
    for client_id, websocket in list(clients.items()):
        await websocket.close()
        logger.info(f"Closed connection to {client_id}")
    
    logger.info("All connections closed. Control should attempt to reconnect.")
```

## Testing Binary Data Handling

### 1. Chunked Binary Transfer

Modify the `send_workflow` function to test chunked binary transfers:

```python
# In send_workflow, replace the binary message sending code with:
# Split the image into chunks
chunk_size = 1024  # Small chunk size to force chunking
chunks = []
for i in range(0, len(img_data), chunk_size):
    chunk = img_data[i:i+chunk_size]
    package_id = workflow["package_id"]
    content_id = f"screen_id_1.png_{i//chunk_size}"
    chunks.append(create_binary_message(package_id, content_id, chunk))

# Send number of chunks in metadata
metadata = {
    "package_id": workflow["package_id"],
    "content_id": "screen_id_1.png",
    "total_chunks": len(chunks),
    "size": len(img_data)
}
await client_socket.send(json.dumps({
    "type": "binary_transfer",
    "data": metadata
}))

# Send each chunk with a delay to simulate network conditions
for i, chunk in enumerate(chunks):
    await client_socket.send(chunk)
    logger.info(f"Sent chunk {i+1}/{len(chunks)}")
    await asyncio.sleep(0.1)  # Small delay between chunks
```

### 2. Corrupted Binary Data

Test how Control handles corrupted binary data:

```python
async def send_corrupted_binary(device_id: str):
    """Send corrupted binary data to test error handling"""
    if not clients:
        logger.error("No clients connected")
        return
    
    client_socket = next(iter(clients.values()))
    
    try:
        # Create package ID
        package_id = f"package_{uuid.uuid4().hex[:8]}"
        content_id = "corrupted_image.png"
        
        # Create corrupted PNG header followed by random data
        corrupted_data = b'\x89PNG\r\n\x1a\n' + os.urandom(1000)
        
        # Send as binary
        binary_msg = create_binary_message(package_id, content_id, corrupted_data)
        await client_socket.send(binary_msg)
        
        logger.info(f"Sent corrupted binary data")
        
    except Exception as e:
        logger.error(f"Error sending corrupted binary: {e}")
```

## Testing Recovery Scenarios

### 1. Unknown Screen Recovery

Test Control's handling of unknown screens:

```python
async def force_unknown_screen(device_id: str):
    """Send a workflow with reference images that won't match any screen"""
    if not clients:
        logger.error("No clients connected")
        return
    
    client_socket = next(iter(clients.values()))
    
    try:
        # Create workflow package with verification
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
        
        # Create an image that won't match any screen
        from PIL import Image, ImageDraw
        
        # All black image - unlikely to match any screen
        img = Image.new('RGB', (1080, 1920), color='black')
        
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
        logger.info(f"Sent non-matching reference image for workflow")
        
    except Exception as e:
        logger.error(f"Error sending non-matching workflow: {e}")
```

### 2. Inject Recovery Script

Test Control's ability to execute recovery scripts:

```python
async def send_recovery_script(device_id: str, workflow_id: str):
    """Send a recovery script to Control"""
    if not clients:
        logger.error("No clients connected")
        return
    
    client_socket = next(iter(clients.values()))
    
    try:
        # Create recovery script package
        script = {
            "package_type": "recovery_script",
            "package_id": f"package_{uuid.uuid4().hex[:8]}",
            "script": {
                "script_id": f"script_{uuid.uuid4().hex[:8]}",
                "workflow_id": workflow_id,
                "code": """
import time
import os
import sys

def main():
    device_id = os.environ.get('CONTROL_DEVICE_ID')
    workflow_id = os.environ.get('CONTROL_WORKFLOW_ID')
    failed_step = os.environ.get('CONTROL_CONTEXT_FAILED_STEP_ID')
    
    print(f"Running recovery script for device {device_id} in workflow {workflow_id}")
    print(f"Failed at step: {failed_step}")
    
    # Simulate recovery actions
    time.sleep(1)
    
    # Press back button to get to a known state
    from ..device_manager import DeviceManager
    device_manager = DeviceManager()
    success, _ = device_manager.execute_command(device_id, ["shell", "input keyevent 4"])
    time.sleep(1)
    
    # Take a screenshot to verify state
    screenshot = device_manager.capture_screenshot(device_id)
    
    # Return success
    result = {
        "status": "success",
        "data": {
            "message": "Recovery successful",
            "timestamp": time.time()
        }
    }
    
    return result

# Set result to be returned
result = main()
""",
                "context": {
                    "last_known_screen": "screen_id_1",
                    "failed_step_id": "step_1234"
                }
            },
            "device_id": device_id,
            "timestamp": str(time.time())
        }
        
        # Send to client
        await client_socket.send(json.dumps({
            "type": "recovery_script",
            "data": script
        }))
        
        logger.info(f"Sent recovery script to device {device_id}")
        
    except Exception as e:
        logger.error(f"Error sending recovery script: {e}")
```

## Testing Conditional Logic

### 1. Workflow with Conditional Steps

Test Control's ability to handle workflows with conditional logic:

```python
def create_conditional_workflow(device_id: str) -> Dict[str, Any]:
    """Create a workflow with conditional logic"""
    workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
    sequence_1_id = f"sequence_{uuid.uuid4().hex[:8]}"
    sequence_2_id = f"sequence_{uuid.uuid4().hex[:8]}"
    
    return {
        "package_type": "workflow",
        "package_id": f"package_{uuid.uuid4().hex[:8]}",
        "workflow": {
            "workflow_id": workflow_id,
            "name": "Conditional Workflow",
            "sequences": [
                {
                    "sequence_id": sequence_1_id,
                    "name": "Main Sequence",
                    "steps": [
                        {
                            "step_id": f"step_{uuid.uuid4().hex[:8]}",
                            "type": "tap",
                            "coordinates": [540, 960],
                            "expected_screen_after": "screen_id_1"
                        }
                    ]
                },
                {
                    "sequence_id": sequence_2_id,
                    "name": "Alternative Sequence",
                    "steps": [
                        {
                            "step_id": f"step_{uuid.uuid4().hex[:8]}",
                            "type": "tap",
                            "coordinates": [200, 500],
                            "expected_screen_after": "screen_id_2"
                        }
                    ]
                }
            ],
            "conditional_logic": [
                {
                    "condition_id": "condition_1",
                    "after_step_id": "step_1",
                    "condition_type": "screen_match",
                    "screen_id": "screen_id_1",
                    "if_true": "continue",
                    "if_false": sequence_2_id
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
            },
            "screen_id_2": {
                "name": "Alternative Screen",
                "image": "screen_id_2.png",
                "validation_regions": [
                    {"x1": 150, "y1": 250, "x2": 350, "y2": 450}
                ]
            }
        },
        "device_id": device_id
    }
```

### 2. Test Multiple Devices

Test Control's ability to handle multiple devices concurrently:

```python
async def multi_device_test(device_ids: List[str]):
    """Test running workflows on multiple devices concurrently"""
    if not clients:
        logger.error("No clients connected")
        return
    
    client_socket = next(iter(clients.values()))
    
    try:
        # Send workflows to each device
        for device_id in device_ids:
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
            
            logger.info(f"Sent workflow to device {device_id}")
            
            # Sleep briefly to avoid overwhelming the client
            await asyncio.sleep(0.5)
            
    except Exception as e:
        logger.error(f"Error in multi-device test: {e}")
```

## Performance Testing

### 1. High Message Volume Test

Test Control's ability to handle a high volume of messages:

```python
async def high_volume_test(device_id: str, count: int = 100):
    """Test sending a high volume of commands in rapid succession"""
    if not clients:
        logger.error("No clients connected")
        return
    
    client_socket = next(iter(clients.values()))
    
    try:
        logger.info(f"Starting high volume test: {count} tap commands")
        
        start_time = time.time()
        
        # Send multiple commands rapidly
        for i in range(count):
            command = create_live_command(
                device_id, 
                "tap", 
                [random.randint(100, 980), random.randint(100, 1820)]
            )
            
            await client_socket.send(json.dumps({
                "type": "live_command",
                "data": command
            }))
            
            # Minimal delay to avoid overwhelming socket
            await asyncio.sleep(0.01)
            
        elapsed = time.time() - start_time
        logger.info(f"Sent {count} commands in {elapsed:.2f} seconds ({count/elapsed:.2f} msgs/sec)")
        
    except Exception as e:
        logger.error(f"Error in high volume test: {e}")
```

### 2. Large Binary Data Test

Test Control's ability to handle large binary payloads:

```python
async def large_binary_test(device_id: str, size_mb: float = 10.0):
    """Test sending a large binary payload"""
    if not clients:
        logger.error("No clients connected")
        return
    
    client_socket = next(iter(clients.values()))
    
    try:
        # Generate large random data
        size_bytes = int(size_mb * 1024 * 1024)
        logger.info(f"Generating {size_mb}MB of test data...")
        
        # Create a large test image instead of random data
        from PIL import Image, ImageDraw
        
        # Calculate dimensions for the requested size (approx)
        # Each pixel is 3 bytes (RGB)
        side = int(math.sqrt(size_bytes / 3))
        
        # Create large image with gradient
        img = Image.new('RGB', (side, side), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw something in the image to make it compressible
        for x in range(0, side, 10):
            for y in range(0, side, 10):
                color = (x % 256, y % 256, (x + y) % 256)
                draw.rectangle([x, y, x+9, y+9], fill=color)
        
        # Save to temp file
        img_path = Path("temp")
        img_path.mkdir(exist_ok=True)
        
        temp_img_path = img_path / "large_test.png"
        img.save(temp_img_path)
        
        # Read image data
        with open(temp_img_path, "rb") as f:
            img_data = f.read()
        
        logger.info(f"Generated image of size {len(img_data)/1024/1024:.2f}MB")
        
        # Create package
        package_id = f"package_{uuid.uuid4().hex[:8]}"
        content_id = "large_test.png"
        
        # Send metadata
        await client_socket.send(json.dumps({
            "type": "binary_transfer",
            "data": {
                "package_id": package_id,
                "content_id": content_id,
                "size": len(img_data),
                "description": "Large binary test"
            }
        }))
        
        # Send binary data
        start_time = time.time()
        binary_msg = create_binary_message(package_id, content_id, img_data)
        await client_socket.send(binary_msg)
        elapsed = time.time() - start_time
        
        logger.info(f"Sent {len(img_data)/1024/1024:.2f}MB in {elapsed:.2f} seconds ({len(img_data)/elapsed/1024/1024:.2f}MB/sec)")
        
    except Exception as e:
        logger.error(f"Error in large binary test: {e}")
```

## Adding These Tests to the Simulator

To add these tests to the Compute Simulator, add them to the `interactive_console` function:

```python
async def interactive_console():
    """Interactive console for sending commands"""
    while True:
        print("\nCommands:")
        print("1. Send workflow")
        print("2. Send live command")
        print("3. Send special sequence")
        print("4. List connected clients")
        print("5. List device statuses")
        print("6. Advanced testing menu")
        print("7. Exit")
        
        choice = await asyncio.get_event_loop().run_in_executor(
            None, lambda: input("Enter choice: ")
        )
        
        # ... existing options ...
        
        elif choice == "6":
            await advanced_testing_menu()
            
        elif choice == "7":
            print("Exiting...")
            return
            
        else:
            print("Invalid choice")

async def advanced_testing_menu():
    """Menu for advanced testing options"""
    while True:
        print("\nAdvanced Testing:")
        print("1. Send malformed workflow")
        print("2. Send to invalid device")
        print("3. Simulate connection drop")
        print("4. Test chunked binary transfer")
        print("5. Send corrupted binary")
        print("6. Force unknown screen")
        print("7. Send recovery script")
        print("8. Test conditional workflow")
        print("9. Multi-device test")
        print("10. High volume test")
        print("11. Large binary test")
        print("12. Back to main menu")
        
        choice = await asyncio.get_event_loop().run_in_executor(
            None, lambda: input("Enter choice: ")
        )
        
        if choice == "1":
            device_id = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Enter device ID: ")
            )
            await send_malformed_workflow(device_id)
            
        # ... other options ...
        
        elif choice == "12":
            return
            
        else:
            print("Invalid choice")
```

These advanced testing scenarios will help you thoroughly test Control's behavior under various conditions, including error cases, edge cases, and performance limits.
