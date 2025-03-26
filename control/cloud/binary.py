"""
Binary data transfer for Cloud communication.
Handles binary message formatting and processing.
"""

import logging
import struct
from typing import Dict, Tuple, Optional, Any, Union
import io

from ..config import Config

class BinaryTransfer:
    """
    Handles binary data transfer over WebSocket.
    """
    
    def __init__(self):
        # Get configuration
        self.config = Config()
        
        # Initialize logging
        self.logger = logging.getLogger("BinaryTransfer")
        
        # Header format: 4 bytes package_id, 4 bytes content_id, 4 bytes content_length
        self.HEADER_FORMAT = "!III"
        self.HEADER_SIZE = struct.calcsize(self.HEADER_FORMAT)
        
        # Maximum chunk size for large transfers (1MB)
        self.MAX_CHUNK_SIZE = self.config.get('cloud.max_chunk_size', 1024 * 1024)
        
        # Temporary storage for fragmented transfers
        self._fragment_buffer = {}  # package_id -> {content_id -> [fragments]}
    
    def create_binary_message(self, package_id: str, content_id: str, 
                             data: bytes) -> bytes:
        """
        Create binary message with header
        
        Args:
            package_id: Package identifier (must be convertible to int)
            content_id: Content identifier (must be convertible to int)
            data: Binary data
            
        Returns:
            Binary message with header
        """
        try:
            # Convert string IDs to integers
            package_id_int = int(package_id, 16) if isinstance(package_id, str) else package_id
            content_id_int = int(content_id, 16) if isinstance(content_id, str) else content_id
            
            # Create header
            header = struct.pack(
                self.HEADER_FORMAT,
                package_id_int,
                content_id_int,
                len(data)
            )
            
            # Combine header and data
            return header + data
            
        except Exception as e:
            self.logger.error(f"Error creating binary message: {e}")
            raise
    
    def process_binary_message(self, data: bytes) -> Tuple[str, str, bytes]:
        """
        Process binary message
        
        Args:
            data: Binary message with header
            
        Returns:
            Tuple of (package_id, content_id, content)
        """
        try:
            # Parse header
            if len(data) < self.HEADER_SIZE:
                raise ValueError("Binary message too small for header")
            
            header = struct.unpack(self.HEADER_FORMAT, data[:self.HEADER_SIZE])
            package_id_int, content_id_int, content_length = header
            
            # Convert integers to hex strings for convenience
            package_id = format(package_id_int, 'x')
            content_id = format(content_id_int, 'x')
            
            # Extract content
            content = data[self.HEADER_SIZE:]
            
            # Verify content length
            if len(content) != content_length:
                raise ValueError(f"Content length mismatch: {len(content)} != {content_length}")
            
            return package_id, content_id, content
            
        except Exception as e:
            self.logger.error(f"Error processing binary message: {e}")
            raise
    
    def chunk_binary_data(self, package_id: str, content_id: str, 
                         data: bytes) -> list[bytes]:
        """
        Split large binary data into chunks with appropriate headers
        
        Args:
            package_id: Package identifier
            content_id: Content identifier
            data: Binary data
            
        Returns:
            List of binary chunks with headers
        """
        chunks = []
        
        # Calculate number of chunks
        total_size = len(data)
        num_chunks = (total_size + self.MAX_CHUNK_SIZE - 1) // self.MAX_CHUNK_SIZE
        
        for i in range(num_chunks):
            # Calculate chunk start and end
            chunk_start = i * self.MAX_CHUNK_SIZE
            chunk_end = min(chunk_start + self.MAX_CHUNK_SIZE, total_size)
            
            # Extract chunk data
            chunk_data = data[chunk_start:chunk_end]
            
            # Create chunk identifier (content_id + chunk number)
            chunk_content_id = f"{content_id}_{i}"
            
            # Create binary message
            chunk = self.create_binary_message(package_id, chunk_content_id, chunk_data)
            chunks.append(chunk)
        
        return chunks
    
    def reassemble_chunks(self, package_id: str, content_id: str, 
                          chunk: bytes) -> Optional[bytes]:
        """
        Process chunk and reassemble if all chunks received
        
        Args:
            package_id: Package identifier
            content_id: Content identifier (with chunk number)
            chunk: Chunk data
            
        Returns:
            Reassembled data if complete, None if still waiting for chunks
        """
        try:
            # Parse chunk number
            if "_" not in content_id:
                # Not a chunked transfer
                return chunk
            
            base_content_id, chunk_num = content_id.rsplit("_", 1)
            chunk_num = int(chunk_num)
            
            # Initialize fragment buffer if needed
            if package_id not in self._fragment_buffer:
                self._fragment_buffer[package_id] = {}
            
            if base_content_id not in self._fragment_buffer[package_id]:
                self._fragment_buffer[package_id][base_content_id] = {}
            
            # Store chunk
            self._fragment_buffer[package_id][base_content_id][chunk_num] = chunk
            
            # Check if all chunks received
            chunks = self._fragment_buffer[package_id][base_content_id]
            
            # TODO: This assumes we know the total number of chunks
            # In practice, we'd need metadata about total chunks
            
            # For now, let's assume we're done if we haven't received a new
            # chunk in a while or if we have a reasonable number of chunks
            # This is a simplification and should be improved
            
            return None  # Still waiting for chunks
            
        except Exception as e:
            self.logger.error(f"Error reassembling chunks: {e}")
            return None
