"""
Pytest configuration and fixtures for Control component testing.
"""

import json
import logging
import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, Generator

from utils.workflow_builder import WorkflowBuilder
from utils.cloud_simulator import CloudSimulator
from utils.device_simulator import DeviceSimulator

# Load test configuration
@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Load test configuration"""
    config_file = Path(__file__).parent / "data" / "configs" / "test_config.json"
    if not config_file.exists():
        # Copy example config if not exists
        example_config = config_file.parent / "test_config.example.json"
        if example_config.exists():
            config_file.write_text(example_config.read_text())
        else:
            raise FileNotFoundError("Test configuration not found")
    
    with open(config_file) as f:
        return json.load(f)

# Setup logging
@pytest.fixture(scope="session", autouse=True)
def setup_logging(test_config):
    """Configure test logging"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    log_level = getattr(logging, test_config["test_environment"]["log_level"])
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "test_run.log"),
            logging.StreamHandler()
        ]
    )

# Cloud simulator
@pytest.fixture(scope="function")
def cloud_sim(test_config, request) -> Generator[CloudSimulator, None, None]:
    """Create Cloud simulator instance"""
    config = test_config["cloud_simulator"]
    
    # Use a different port for each test to avoid conflicts
    # Base port from config + test node id hash to get a unique port
    base_port = config["port"]
    node_id = request.node.nodeid
    port_offset = hash(node_id) % 1000  # Keep offset within reasonable range
    test_port = base_port + port_offset
    
    simulator = CloudSimulator(
        host=config["host"],
        port=test_port
    )
    
    # Start simulator
    simulator.start_background()
    
    yield simulator
    
    # Stop simulator
    simulator.stop_background()

# Device simulator
@pytest.fixture(scope="function")
def device_sim(test_config) -> Generator[DeviceSimulator, None, None]:
    """Create device simulator instance"""
    config = test_config["device_simulator"]["devices"][0]  # Use first device
    simulator = DeviceSimulator(device_id=config["id"])
    
    # Configure screen
    simulator.set_screen_state(**config["screen"])
    
    # Start simulator
    simulator.start()
    
    yield simulator
    
    # Stop simulator
    simulator.stop()

# Multiple device simulators
@pytest.fixture(scope="function")
def device_sims(test_config) -> Generator[Dict[str, DeviceSimulator], None, None]:
    """Create multiple device simulator instances"""
    simulators = {}
    
    for device_config in test_config["device_simulator"]["devices"]:
        device_id = device_config["id"]
        simulator = DeviceSimulator(device_id=device_id)
        simulator.set_screen_state(**device_config["screen"])
        simulator.start()
        simulators[device_id] = simulator
    
    yield simulators
    
    # Stop all simulators
    for simulator in simulators.values():
        simulator.stop()

# Workflow builder
@pytest.fixture(scope="function")
def workflow_builder(test_config) -> WorkflowBuilder:
    """Create workflow builder instance"""
    config = test_config["workflow_builder"]
    return WorkflowBuilder(
        encryption_key=config["encryption_key"]
    )

# Test data paths
@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Get test data directory"""
    return Path(__file__).parent / "data"

@pytest.fixture(scope="session")
def screenshots_dir(test_data_dir) -> Path:
    """Get screenshots directory"""
    return test_data_dir / "screenshots"

@pytest.fixture(scope="session")
def workflows_dir(test_data_dir) -> Path:
    """Get workflows directory"""
    return test_data_dir / "workflows"

# Cleanup
@pytest.fixture(scope="function", autouse=True)
def cleanup(test_config, test_data_dir):
    """Clean up test artifacts"""
    yield
    
    if test_config["test_environment"]["cleanup_after_tests"]:
        # Clean up temporary files
        temp_dir = test_data_dir / "temp"
        if temp_dir.exists():
            for file in temp_dir.iterdir():
                if file.is_file():
                    file.unlink()

# Event loop
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
