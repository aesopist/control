# Integrating the TikTok Workflow with Compute Simulator

This guide explains how to integrate the TikTok workflow example with your Compute Simulator for more realistic testing of Control.

## Step 1: Import the TikTok Workflow Module

Modify your `compute_simulator.py` to import the TikTok workflow module:

```python
# Add at the top of compute_simulator.py
import importlib.util
import sys

# Dynamically import the TikTok workflow module
try:
    spec = importlib.util.spec_from_file_location("tiktok_workflow", "tiktok_example_workflow.py")
    tiktok_workflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tiktok_workflow)
    TIKTOK_WORKFLOW_AVAILABLE = True
except Exception as e:
    print(f"Error importing TikTok workflow: {e}")
    TIKTOK_WORKFLOW_AVAILABLE = False
```

## Step 2: Add Client Socket Setter

Add a setter for the client socket in the `handle_client_messages` function:

```python
async def handle_client_messages(websocket, path):
    """Handle messages from Control client"""
    client_id = None
    
    try:
        # ... existing code ...
        
        # Set client socket for TikTok workflow
        if TIKTOK_WORKFLOW_AVAILABLE:
            tiktok_workflow.setup_tiktok_workflow.client_socket = websocket
        
        # ... existing code ...
```

## Step 3: Add TikTok Workflow to Interactive Console

Add a TikTok workflow option to your interactive console:

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
        print("7. Run TikTok post workflow")  # New option
        print("8. Exit")
        
        choice = await asyncio.get_event_loop().run_in_executor(
            None, lambda: input("Enter choice: ")
        )
        
        # ... existing options ...
        
        elif choice == "7":
            if not TIKTOK_WORKFLOW_AVAILABLE:
                print("TikTok workflow module not available.")
                continue
                
            device_id = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Enter device ID: ")
            )
            await tiktok_workflow.setup_tiktok_workflow(device_id)
            
        elif choice == "8":
            print("Exiting...")
            return
            
        # ... rest of function ...
```

## Step 4: Run the Modified Simulator

1. Ensure both `compute_simulator.py` and `tiktok_example_workflow.py` are in the same directory
2. Run the simulator:

```
python compute_simulator.py
```

3. When Control connects, you can select option 7 to send the TikTok workflow

## Features of the TikTok Workflow

The TikTok workflow example provides several realistic testing aspects:

1. **Complex Workflow Structure**: Multiple sequences with conditional logic
2. **Generated Test Images**: Creates mock TikTok screens for testing
3. **Special Sequence**: Includes a special sequence for waiting for post completion
4. **Error Handling**: Has branches for handling permissions and errors
5. **Clipboard Integration**: Tests the keyboard clipboard functionality

## Using for Test Automation

You can also automate the testing by modifying the simulator:

```python
async def run_automated_tiktok_test():
    """Run automated TikTok workflow test"""
    if not clients or not TIKTOK_WORKFLOW_AVAILABLE:
        logger.error("No clients connected or TikTok workflow not available")
        return
    
    # Wait for client to be properly initialized
    await asyncio.sleep(2)
    
    # Get list of connected devices
    device_statuses = {}  # This should be populated in your handle_client_messages
    if not device_statuses:
        logger.error("No devices available")
        return
    
    # Run test on first available device
    device_id = next(iter(device_statuses.keys()))
    logger.info(f"Running automated TikTok workflow test on device {device_id}")
    
    workflow_id = await tiktok_workflow.setup_tiktok_workflow(device_id)
    if workflow_id:
        logger.info(f"Successfully started TikTok workflow {workflow_id}")
    else:
        logger.error("Failed to start TikTok workflow")
```

Add this function to `main()` to run it automatically when desired:

```python
async def main(host: str, port: int, run_automated_test: bool = False):
    """Main function"""
    # Start server
    server = await websockets.serve(handle_client_messages, host, port)
    logger.info(f"Server running at ws://{host}:{port}")
    
    # Run automated test if requested
    if run_automated_test and TIKTOK_WORKFLOW_AVAILABLE:
        # Wait a bit for client to connect
        await asyncio.sleep(5)
        if clients:
            await run_automated_tiktok_test()
    
    # Start interactive console
    console_task = asyncio.create_task(interactive_console())
    
    # Run forever
    try:
        await console_task
    finally:
        server.close()
        await server.wait_closed()
```

Then add a command-line argument for automated testing:

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute Simulator for Control testing")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind server to")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind server to")
    parser.add_argument("--auto-test", action="store_true", help="Run automated TikTok test on startup")
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.host, args.port, args.auto_test))
    except KeyboardInterrupt:
        logger.info("Server stopped")
```

This allows you to run automated testing with:

```
python compute_simulator.py --auto-test
```

The TikTok workflow example provides a more realistic test case that exercises many aspects of Control, including screen verification, special sequences, conditional logic, and device interactions.
