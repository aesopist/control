"""
Main entry point for Control component.
Initializes components and starts control system.
"""

import sys
import os
import argparse
import logging
import signal
import time
from pathlib import Path

# Add parent directory to path for imports
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from control.config import Config
from control.device_manager import DeviceManager
from control.cloud import CloudClient
from control.verification import ScreenVerifier, ScreenRegistry
from control.workflows import WorkflowExecutor
from control.keyboard import KeyboardClient

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Control - Device Automation Agent")
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local compute for development (instead of Cloud)"
    )
    
    return parser.parse_args()

def setup_logging(debug_mode=False):
    """Configure logging"""
    # Determine log level
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set up file handler for persistent logs
    base_path = Path(__file__).parent.parent
    logs_path = base_path / "logs"
    logs_path.mkdir(exist_ok=True)
    
    log_file = logs_path / "control.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    # Adjust external library logging
    logging.getLogger("websockets").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("requests").setLevel(logging.INFO)

def signal_handler(signum, frame):
    """Handle termination signals"""
    logger = logging.getLogger("Control")
    logger.info(f"Received signal {signum}, shutting down...")
    
    # Stop components
    cloud_client = CloudClient()
    cloud_client.stop()
    
    workflow_executor = WorkflowExecutor()
    workflow_executor.stop()
    
    # Exit
    sys.exit(0)

def main():
    """Main entry point"""
    try:
        # Parse arguments
        args = parse_args()
        
        # Set up logging
        setup_logging(args.debug)
        logger = logging.getLogger("Control")
        
        # Log startup
        logger.info("Starting Control...")
        
        # Load configuration
        config = Config()
        if args.config:
            config_path = Path(args.config)
            if not config_path.exists():
                logger.error(f"Configuration file not found: {args.config}")
                return 1
            # TODO: Load custom config
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initialize core components
        logger.info("Initializing components...")
        
        # Initialize device manager
        device_manager = DeviceManager()
        
        # Initialize cloud client
        cloud_client = CloudClient()
        
        # Initialize live command handler and register with cloud client
        from control.cloud.protocol import MessageType
        from control.live.handler import LiveCommandHandler
        live_handler = LiveCommandHandler()
        cloud_client.register_callback(MessageType.LIVE_COMMAND, live_handler.handle_command)
        
        # Initialize workflow executor (which initializes other components)
        workflow_executor = WorkflowExecutor()
        
        # List connected devices
        logger.info("Checking connected devices...")
        devices = device_manager.get_available_devices()
        
        if devices:
            logger.info(f"Found {len(devices)} connected devices:")
            for device_id, device_info in devices.items():
                logger.info(f"  - {device_info.get('friendly_name', 'Unknown')} ({device_id})")
        else:
            logger.warning("No devices connected")
        
        # Start device monitoring
        device_manager.start_monitoring()
        logger.info("Device monitoring started")
        
        # Keep running until terminated
        logger.info("Control system running. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        signal_handler(signal.SIGINT, None)
        
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
