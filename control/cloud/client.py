"""
Cloud client for Control component.
Handles WebSocket communication with Cloud relay service.
"""

import json
import logging
import asyncio
import websockets
import threading
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Union
from queue import Queue

from ..config import Config
from .protocol import MessageType, Message
from .binary import BinaryTransfer

class CloudClient:
    """
    Handles communication with Cloud relay service.
    Implements the Singleton pattern to ensure one connection per Control instance.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CloudClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Get configuration
        self.config = Config()
        
        # Initialize logging
        self.logger = logging.getLogger("CloudClient")
        
        # Connection state
        self._connected = False
        self._ws = None
        self._stop_event = threading.Event()
        
        # Message queues
        self._outgoing_queue = Queue()
        self._response_queues: Dict[str, Queue] = {}
        
        # Callback registry
        self._message_callbacks: Dict[MessageType, List[Callable]] = {
            msg_type: [] for msg_type in MessageType
        }
        
        # Binary transfer handler
        self.binary_transfer = BinaryTransfer()
        
        # Start connection thread
        self._connection_thread = threading.Thread(target=self._run_connection, daemon=True)
        self._connection_thread.start()
        
        self._initialized = True
    
    def _run_connection(self):
        """Main connection loop running in separate thread"""
        while not self._stop_event.is_set():
            try:
                # Create event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run connection handling
                loop.run_until_complete(self._handle_connection())
                
            except Exception as e:
                self.logger.error(f"Connection error: {e}")
                
            finally:
                # Clean up
                if loop:
                    loop.close()
                
            # Wait before reconnecting
            if not self._stop_event.is_set():
                reconnect_interval = self.config.get('cloud.reconnect_interval', 5)
                time.sleep(reconnect_interval)
    
    async def _handle_connection(self):
        """Handle WebSocket connection and message processing"""
        url = self.config.get('cloud.url')
        if not url:
            self.logger.error("Cloud relay URL not configured")
            return
            
        # Add client identification to URL
        client_id = self.config.get('client.id', 'control')
        url = f"{url}?client_id={client_id}"
        
        try:
            async with websockets.connect(url) as ws:
                self._ws = ws
                self._connected = True
                self.logger.info("Connected to Cloud relay")
                
                # Start ping task
                ping_task = asyncio.create_task(self._ping_loop())
                
                try:
                    # Start message processing tasks
                    incoming_task = asyncio.create_task(self._process_incoming())
                    outgoing_task = asyncio.create_task(self._process_outgoing())
                    
                    # Wait for any task to complete or connection to close
                    done, pending = await asyncio.wait(
                        [ping_task, incoming_task, outgoing_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel remaining tasks
                    for task in pending:
                        task.cancel()
                        
                except Exception as e:
                    self.logger.error(f"Error during connection: {e}")
                
                finally:
                    self._connected = False
                    self._ws = None
                    self.logger.info("Disconnected from Cloud relay")
        
        except Exception as e:
            self.logger.error(f"Error connecting to Cloud relay: {e}")
    
    async def _ping_loop(self):
        """Send periodic pings to keep connection alive"""
        ping_interval = self.config.get('cloud.ping_interval', 30)
        
        while True:
            try:
                if self._ws and not self._ws.closed:
                    await self._ws.send(json.dumps({
                        "type": MessageType.PING.value,
                        "data": {}
                    }))
                await asyncio.sleep(ping_interval)
            except Exception as e:
                self.logger.error(f"Ping error: {e}")
                break
    
    async def _process_incoming(self):
        """Process incoming messages from Cloud"""
        while True:
            try:
                if not self._ws or self._ws.closed:
                    break
                    
                # Wait for message
                message = await self._ws.recv()
                
                # Check if binary message
                if isinstance(message, bytes):
                    # Handle binary message
                    await self._handle_binary_message(message)
                    continue
                
                # Parse JSON message
                msg_data = json.loads(message)
                
                # Create Message object
                try:
                    msg_type = MessageType(msg_data.get('type'))
                    msg = Message(
                        type=msg_type,
                        data=msg_data.get('data', {}),
                        id=msg_data.get('id'),
                        device_id=msg_data.get('device_id')
                    )
                except ValueError:
                    self.logger.error(f"Unknown message type: {msg_data.get('type')}")
                    continue
                
                # Handle pong responses
                if msg_type == MessageType.PONG:
                    continue
                
                # Check for response queue
                if msg.id and msg.id in self._response_queues:
                    self._response_queues[msg.id].put(msg)
                    continue
                
                # Trigger callbacks
                for callback in self._message_callbacks[msg_type]:
                    try:
                        callback(msg)
                    except Exception as e:
                        self.logger.error(f"Callback error: {e}")
                
            except Exception as e:
                self.logger.error(f"Error processing incoming message: {e}")
                break
    
    async def _handle_binary_message(self, data: bytes):
        """Handle binary message from Cloud"""
        try:
            # Process with binary transfer handler
            package_id, content_id, content = self.binary_transfer.process_binary_message(data)
            
            # Notify callbacks
            for callback in self._message_callbacks[MessageType.BINARY]:
                try:
                    callback(Message(
                        type=MessageType.BINARY,
                        data={
                            'package_id': package_id,
                            'content_id': content_id,
                            'content': content
                        }
                    ))
                except Exception as e:
                    self.logger.error(f"Binary callback error: {e}")
            
        except Exception as e:
            self.logger.error(f"Error processing binary message: {e}")
    
    async def _process_outgoing(self):
        """Process outgoing messages to Cloud"""
        while True:
            try:
                if not self._ws or self._ws.closed:
                    break
                    
                # Get message from queue
                msg = await asyncio.get_event_loop().run_in_executor(
                    None, self._outgoing_queue.get
                )
                
                # Check if binary message
                if isinstance(msg, bytes):
                    await self._ws.send(msg)
                    continue
                
                # Send JSON message
                await self._ws.send(json.dumps({
                    "type": msg.type.value,
                    "data": msg.data,
                    "id": msg.id,
                    "device_id": msg.device_id
                }))
                
            except Exception as e:
                self.logger.error(f"Error processing outgoing message: {e}")
                break
    
    def send_message(self, msg: Message, timeout: Optional[int] = None) -> Optional[Message]:
        """
        Send message to Cloud and optionally wait for response
        
        Args:
            msg: Message to send
            timeout: Optional timeout to wait for response in seconds
            
        Returns:
            Response message if timeout specified, None otherwise
        """
        if not self._connected:
            self.logger.error("Not connected to Cloud relay")
            return None
        
        # Generate message ID if not provided
        if not msg.id:
            msg.id = str(uuid.uuid4())
        
        # Create response queue if waiting for response
        if timeout is not None:
            self._response_queues[msg.id] = Queue()
        
        # Add to outgoing queue
        self._outgoing_queue.put(msg)
        
        # Wait for response if timeout specified
        if timeout is not None:
            try:
                response = self._response_queues[msg.id].get(timeout=timeout)
                return response
            except Exception as e:
                self.logger.error(f"Timeout waiting for response: {e}")
                return None
            finally:
                # Remove response queue
                self._response_queues.pop(msg.id, None)
        
        return None
    
    def send_binary(self, package_id: str, content_id: str, 
                   data: bytes, timeout: Optional[int] = None) -> bool:
        """
        Send binary data to Cloud
        
        Args:
            package_id: Package identifier
            content_id: Content identifier within package
            data: Binary data to send
            timeout: Optional timeout for acknowledgment
            
        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            self.logger.error("Not connected to Cloud relay")
            return False
        
        try:
            # Format binary message
            binary_message = self.binary_transfer.create_binary_message(
                package_id, content_id, data
            )
            
            # Add to outgoing queue
            self._outgoing_queue.put(binary_message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending binary data: {e}")
            return False
    
    def register_callback(self, msg_type: MessageType, callback: Callable[[Message], None]):
        """
        Register callback for message type
        
        Args:
            msg_type: Message type to handle
            callback: Function to call when message is received
        """
        self._message_callbacks[msg_type].append(callback)
    
    def unregister_callback(self, msg_type: MessageType, callback: Callable[[Message], None]):
        """
        Unregister callback for message type
        
        Args:
            msg_type: Message type
            callback: Function to unregister
        """
        if callback in self._message_callbacks[msg_type]:
            self._message_callbacks[msg_type].remove(callback)
    
    def stop(self):
        """Stop Cloud client"""
        self._stop_event.set()
        
        # Wait for connection thread to finish
        if self._connection_thread and self._connection_thread.is_alive():
            self._connection_thread.join(timeout=5)