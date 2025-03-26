"""
Cloud relay simulator for testing Control component.
Simulates the Cloud service by providing a WebSocket server that can send and receive messages.
"""

import json
import asyncio
import logging
import threading
import queue
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone
import websockets
from websockets.server import WebSocketServerProtocol
from pathlib import Path

class CloudSimulator:
    """
    Simulates Cloud relay service for testing.
    Provides WebSocket server that can send workflow packages and receive responses.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Initialize Cloud simulator
        
        Args:
            host: Host to bind server to
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self.server = None
        self._stop_event = threading.Event()
        
        # Connected clients
        self._clients: Dict[str, WebSocketServerProtocol] = {}
        
        # Message queues
        self._outgoing_queue = queue.Queue()
        self._incoming_queue = queue.Queue()
        
        # Response tracking
        self._responses: Dict[str, List[Dict[str, Any]]] = {}
        
        # Setup logging
        self.log_dir = Path(__file__).parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("CloudSimulator")
        handler = logging.FileHandler(self.log_dir / "cloud_simulator.log")
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
    
    async def start(self):
        """Start the WebSocket server"""
        self.logger.info(f"Starting Cloud simulator on {self.host}:{self.port}")
        
        try:
            self.server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port
            )
            self.logger.info("Cloud simulator running")
            
        except Exception as e:
            self.logger.error(f"Failed to start Cloud simulator: {e}")
            raise
    
    def start_background(self):
        """Start server in background thread"""
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Start server
            loop.run_until_complete(self.start())
            
            # Start message processing
            self._process_outgoing_messages(loop)
            
            # Run event loop
            loop.run_forever()
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def _process_outgoing_messages(self, loop):
        """Process outgoing messages in background"""
        def process_queue():
            try:
                # Check if there are messages to send
                if not self._outgoing_queue.empty():
                    client_id, message = self._outgoing_queue.get_nowait()
                    
                    # Get client websocket
                    if client_id is None:
                        # Send to all clients
                        for ws in self._clients.values():
                            asyncio.run_coroutine_threadsafe(
                                self._send_message(client_id, message), loop
                            )
                    else:
                        # Send to specific client
                        asyncio.run_coroutine_threadsafe(
                            self._send_message(client_id, message), loop
                        )
            except queue.Empty:
                pass
            except Exception as e:
                self.logger.error(f"Error processing outgoing message: {e}")
            
            # Schedule next check
            loop.call_later(0.1, process_queue)
        
        # Start processing
        loop.call_soon(process_queue)
    
    async def stop(self):
        """Stop the WebSocket server"""
        self.logger.info("Stopping Cloud simulator")
        self._stop_event.set()
        
        if self.server:
            self.server.close()
            # Don't wait for server to close, just log and continue
            self.logger.info("Server closed")
        
        self.logger.info("Cloud simulator stopped")
    
    def stop_background(self):
        """Stop server running in background"""
        # Just log and continue, don't try to stop the server
        # This avoids asyncio loop issues
        self.logger.info("Stopping Cloud simulator (background)")
        self._stop_event.set()
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """
        Handle new WebSocket connection
        
        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        # Extract client ID from query params
        query = websockets.uri.parse_uri(str(websocket.path)).query
        client_id = query.get("client_id", ["unknown"])[0]
        
        try:
            # Register client
            self._clients[client_id] = websocket
            self.logger.info(f"Client connected: {client_id}")
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client disconnected: {client_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling connection: {e}")
            
        finally:
            # Unregister client
            self._clients.pop(client_id, None)
    
    async def _handle_message(self, client_id: str, message: str):
        """
        Handle incoming message from client
        
        Args:
            client_id: Client identifier
            message: Message content
        """
        try:
            # Parse message
            if isinstance(message, bytes):
                # Handle binary message
                self.logger.debug(f"Received binary message from {client_id}")
                self._incoming_queue.put(("binary", client_id, message))
                return
            
            data = json.loads(message)
            msg_type = data.get("type")
            
            self.logger.debug(f"Received message from {client_id}: {msg_type}")
            
            # Handle message types
            if msg_type == "PING":
                await self._send_message(client_id, {
                    "type": "PONG",
                    "data": {}
                })
            
            # Store response
            if "id" in data:
                msg_id = data["id"]
                if msg_id not in self._responses:
                    self._responses[msg_id] = []
                self._responses[msg_id].append(data)
            
            # Queue for processing
            self._incoming_queue.put(("json", client_id, data))
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def _send_message(self, client_id: str, message: Any):
        """
        Send message to client
        
        Args:
            client_id: Client identifier
            message: Message to send (dict for JSON or bytes for binary)
        """
        try:
            websocket = self._clients.get(client_id)
            if not websocket:
                self.logger.warning(f"Client not found: {client_id}")
                return
            
            if isinstance(message, (dict, list)):
                # Send JSON message
                await websocket.send(json.dumps(message))
            else:
                # Send binary message
                await websocket.send(message)
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
    
    def send_workflow(
        self,
        workflow_package: Dict[str, Any],
        client_id: Optional[str] = None
    ):
        """
        Send workflow package to client
        
        Args:
            workflow_package: Workflow package to send
            client_id: Optional specific client to send to
        """
        message = {
            "type": "WORKFLOW",
            "data": {
                "action": "start",
                **workflow_package
            },
            "id": workflow_package["package_id"]
        }
        
        self._outgoing_queue.put((client_id, message))
    
    def send_live_command(
        self,
        command_package: Dict[str, Any],
        client_id: Optional[str] = None
    ):
        """
        Send live command package to client
        
        Args:
            command_package: Command package to send
            client_id: Optional specific client to send to
        """
        message = {
            "type": "COMMAND",
            "data": command_package,
            "id": command_package["package_id"]
        }
        
        self._outgoing_queue.put((client_id, message))
    
    # Shared ID mapping with BinaryTransfer for testing
    _id_mapping = {}
    
    def _string_to_int(self, s: str) -> int:
        """
        Convert string to integer hash
        Uses a simple hashing algorithm to generate a 32-bit integer from a string
        
        Args:
            s: String to convert
            
        Returns:
            32-bit integer hash
        """
        # Use a simple hash function that fits in 32 bits
        h = 0
        for c in s:
            h = (31 * h + ord(c)) & 0xFFFFFFFF
        return h

    def send_binary(
        self,
        package_id: str,
        content_id: str,
        data: bytes,
        client_id: Optional[str] = None
    ):
        """
        Send binary data to client
        
        Args:
            package_id: Package identifier
            content_id: Content identifier
            data: Binary data to send
            client_id: Optional specific client to send to
        """
        # Format matches Control's binary frame structure
        import struct
        
        # Convert string IDs to integers using hash function
        package_id_int = self._string_to_int(package_id)
        content_id_int = self._string_to_int(content_id)
        
        # Store original IDs for reverse lookup (for testing only)
        # This is shared with BinaryTransfer._id_mapping
        from control.cloud.binary import BinaryTransfer
        BinaryTransfer._id_mapping[str(package_id_int)] = package_id
        BinaryTransfer._id_mapping[str(content_id_int)] = content_id
        
        # Create header
        header = struct.pack(
            "!III",
            package_id_int,
            content_id_int,
            len(data)
        )
        
        message = header + data
        self._outgoing_queue.put((client_id, message))
    
    def get_responses(
        self,
        package_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Get responses for a package
        
        Args:
            package_id: Optional specific package ID to get responses for
            timeout: Optional timeout in seconds
            
        Returns:
            List of response messages
        """
        if package_id:
            return self._responses.get(package_id, [])
        return [
            resp for resps in self._responses.values()
            for resp in resps
        ]
    
    def clear_responses(self):
        """Clear stored responses"""
        self._responses.clear()
    
    def get_incoming_messages(
        self,
        timeout: Optional[float] = None
    ) -> List[tuple]:
        """
        Get incoming messages
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            List of (type, client_id, message) tuples
        """
        messages = []
        try:
            while True:
                messages.append(self._incoming_queue.get(timeout=timeout))
        except queue.Empty:
            pass
        return messages
    
    def clear_incoming_messages(self):
        """Clear incoming message queue"""
        while not self._incoming_queue.empty():
            self._incoming_queue.get()
