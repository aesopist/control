"""
Unit tests for binary data handling in Control component.
Tests the binary transfer functionality between Control and Cloud.
"""

import pytest
import os
from pathlib import Path
from PIL import Image
import io

from control.cloud.binary import BinaryTransfer
from utils.workflow_builder import WorkflowBuilder
from utils.cloud_simulator import CloudSimulator

def test_binary_frame_creation():
    """Test creating binary frames with headers"""
    binary = BinaryTransfer()
    
    # Test data
    package_id = "test_pkg_1"
    content_id = "test_content_1"
    data = b"Hello, World!"
    
    # Create binary message
    message = binary.create_binary_message(package_id, content_id, data)
    
    # Process message
    result_pkg_id, result_content_id, result_data = binary.process_binary_message(message)
    
    # Verify results
    assert result_pkg_id == package_id
    assert result_content_id == content_id
    assert result_data == data

def test_binary_chunking():
    """Test chunking large binary data"""
    binary = BinaryTransfer()
    
    # Override chunk size for testing
    original_chunk_size = binary.MAX_CHUNK_SIZE
    binary.MAX_CHUNK_SIZE = 10  # Small size for testing
    
    try:
        # Test data
        package_id = "test_pkg_1"
        content_id = "test_content_1"
        data = b"This is a longer message that will be split into chunks"
        
        # Create chunks
        chunks = binary.chunk_binary_data(package_id, content_id, data)
        
        # Verify we got multiple chunks
        assert len(chunks) > 1
        
        # Reassemble chunks
        reassembled = b""
        for i, chunk in enumerate(chunks):
            # Process chunk
            _, chunk_content_id, chunk_data = binary.process_binary_message(chunk)
            
            # Verify chunk ID format
            assert chunk_content_id == f"{content_id}_{i}"
            
            # Add to reassembled data
            reassembled += chunk_data
        
        # Verify reassembled data matches original
        assert reassembled == data
        
    finally:
        # Restore original chunk size
        binary.MAX_CHUNK_SIZE = original_chunk_size

def test_binary_transfer_with_cloud(cloud_sim, workflow_builder, test_data_dir):
    """Test binary data transfer through Cloud simulator"""
    # Create test image
    image_size = (100, 100)
    test_image = Image.new('RGB', image_size, color='red')
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='PNG')
    image_data = img_bytes.getvalue()
    
    # Create package ID
    package_id = "test_pkg_1"
    content_id = "screenshot_1"
    
    # Create binary message directly
    binary = BinaryTransfer()
    message = binary.create_binary_message(package_id, content_id, image_data)
    
    # Process the message
    received_pkg_id, received_content_id, received_data = binary.process_binary_message(message)
    
    # Verify package ID and content ID
    assert received_pkg_id == package_id
    assert received_content_id == content_id
    
    # Verify image data
    assert received_data == image_data
    
    # Verify we can load it as an image
    received_image = Image.open(io.BytesIO(received_data))
    assert received_image.size == image_size

def test_encrypted_workflow_with_binary(cloud_sim, workflow_builder, test_data_dir):
    """Test encrypted workflow package with binary data"""
    # Create test workflow with binary content
    image_size = (100, 100)
    test_image = Image.new('RGB', image_size, color='blue')
    
    # Save test image
    screenshots_dir = test_data_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    test_image_path = screenshots_dir / "test_screen.png"
    test_image.save(test_image_path)
    
    # Create workflow package
    workflow = workflow_builder.create_workflow_package(
        device_id="test_device_1:5555",
        sequences=[
            workflow_builder.create_tap_sequence(
                coordinates_list=[[50, 50]],
                expected_screens=["test_screen"]
            )
        ],
        screen_registry={
            "test_screen": {
                "name": "Test Screen",
                "image": "test_screen.png",
                "validation_regions": [
                    {"x1": 0, "y1": 0, "x2": 100, "y2": 100}
                ]
            }
        },
        media_files=["test_screen.png"],
        encrypt=True
    )
    
    # Verify the workflow package has the expected structure
    assert "encrypted" in workflow
    assert workflow["encrypted"] is True
    assert "salt" in workflow
    assert "content" in workflow
    assert "package_id" in workflow
    
    # Verify we can decrypt it
    decrypted = workflow_builder._decrypt_package(workflow)
    assert "workflow" in decrypted
    assert "screen_registry" in decrypted
    assert "test_screen" in decrypted["screen_registry"]

def test_binary_error_handling():
    """Test error handling in binary transfer"""
    binary = BinaryTransfer()
    
    # Test invalid package ID
    with pytest.raises(Exception):
        binary.create_binary_message(None, "content_1", b"data")
    
    # Test invalid content ID
    with pytest.raises(Exception):
        binary.create_binary_message("pkg_1", None, b"data")
    
    # Test empty data
    with pytest.raises(Exception):
        binary.create_binary_message("pkg_1", "content_1", None)
    
    # Test processing invalid message
    with pytest.raises(Exception):
        binary.process_binary_message(b"invalid")
    
    # Test processing truncated message
    with pytest.raises(Exception):
        binary.process_binary_message(b"short")
    
    # Test processing message with invalid length
    header = binary.create_binary_message("pkg_1", "content_1", b"data")
    with pytest.raises(Exception):
        binary.process_binary_message(header[:binary.HEADER_SIZE])  # Header only
