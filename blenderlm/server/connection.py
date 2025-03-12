import asyncio
import json
import logging
import socket
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("blenderlm.connection")

@dataclass
class BlenderConnection:
    """
    Manages a connection to a Blender instance via the BlenderLM addon.
    """
    host: str
    port: int
    session_id: str | None = None
    sock: socket.socket  | None = None
    last_activity: float  | None = None
    
    def __post_init__(self):
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())
        self.last_activity = time.time()
    
    def connect(self) -> bool:
        """Connect to the Blender addon socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Blender at {self.host}:{self.port} (session: {self.session_id})")
            self.last_activity = time.time()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Blender: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Blender addon"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Blender: {str(e)}")
            finally:
                self.sock = None
    
    def is_connected(self) -> bool:
        """Check if the connection is still active"""
        if not self.sock:
            return False
            
        try:
            # Try to send an empty message as a keepalive
            self.sock.settimeout(1.0)
            # Use a ping command instead of empty data
            ping_cmd = json.dumps({"type": "ping"}).encode('utf-8')
            self.sock.sendall(ping_cmd)
            
            # Wait for response
            try:
                data = self.sock.recv(1024)
                if data:
                    # Update last activity timestamp
                    self.last_activity = time.time()
                    return True
                return False
            except socket.timeout:
                return False
                
        except Exception:
            self.sock = None
            return False
    
    
    # In the BlenderConnection.receive_full_response method:
    def receive_full_response(self, buffer_size=8192, timeout=30.0):  
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        if self.sock is None: 
            raise ConnectionError("Not connected to Blender")
        self.sock.settimeout(timeout)  # Use the increased timeout
        
        try:
            while True:
                try:
                    chunk = self.sock.recv(buffer_size)
                    if not chunk:
                        if not chunks:
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    
                    # Check if we've received a complete JSON object
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        # If parsing succeeded, we have a complete response
                        logger.debug(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    # If we hit a timeout, log it and break
                    logger.warning("Socket timeout during receive operation")
                    break
                except (ConnectionError, BrokenPipeError) as e:
                    logger.error(f"Socket connection error: {str(e)}")
                    raise
        except socket.timeout:
            logger.warning("Socket timeout during receive operation")
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        # Try to use what we have
        if chunks:
            data = b''.join(chunks)
            try:
                # Try to parse what we have
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                # Still raise an exception but provide debug info
                data_preview = data.decode('utf-8')[:100] + "..." if len(data) > 100 else data.decode('utf-8')
                logger.error(f"Incomplete JSON response: {data_preview}")
                raise Exception("Incomplete JSON response received")
        else:
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a command to Blender and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Blender")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            
            # Log the command being sent
            logger.debug(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            if self.sock is None:
                self.connect()
                if self.sock is None:  # If connect failed, sock will still be None
                    raise ConnectionError("Failed to connect to Blender")
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.debug(f"Command sent, waiting for response...")
            
            # Update last activity timestamp
            self.last_activity = time.time()
            
            # Receive the response
            response_data = self.receive_full_response()
            response = json.loads(response_data.decode('utf-8'))
            
            if response.get("status") == "error":
                logger.error(f"Blender error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from Blender"))
            
            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Blender")
            self.sock = None
            raise Exception("Timeout waiting for Blender response")
        except (ConnectionError, BrokenPipeError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Blender lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Blender: {str(e)}")
            raise Exception(f"Invalid response from Blender: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Blender: {str(e)}")
            self.sock = None
            raise Exception(f"Communication error with Blender: {str(e)}")

class BlenderConnectionManager:
    """
    Manages a single connection to Blender from within FastAPI
    """
    def __init__(self, host="localhost", port=9876):
        self.host = host
        self.port = port
        self.connection = BlenderConnection(host=host, port=port)
        self.connection_lock = asyncio.Lock()
        self.is_connected = False
        
    async def ensure_connected(self):
        """Ensure we have a connection to Blender"""
        async with self.connection_lock:
            if not self.is_connected:
                try:
                    logger.info(f"Connecting to Blender at {self.host}:{self.port}")
                    if self.connection.connect():
                        self.is_connected = True
                        logger.info("Connected to Blender successfully")
                    else:
                        logger.error("Failed to connect to Blender")
                except Exception as e:
                    logger.error(f"Error connecting to Blender: {e}")
                    self.is_connected = False
            
            return self.is_connected
                
    async def send_command(self, command_type: str, params: Optional[Dict[str, Any]] = None):
        """Send a command to Blender"""
        async with self.connection_lock:
            # Make sure we're connected
            if not self.is_connected:
                if not await self.ensure_connected():
                    raise ConnectionError("Could not connect to Blender")
            
            # Send the command
            try:
                return self.connection.send_command(command_type, params)
            except Exception as e:
                # Mark as disconnected if there was an error
                self.is_connected = False
                raise e

