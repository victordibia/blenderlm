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
    
    def receive_full_response(self, buffer_size=32768, timeout=120.0):  
        """Receive the complete response, potentially in multiple chunks"""
        chunks = []
        if self.sock is None: 
            raise ConnectionError("Not connected to Blender")
        self.sock.settimeout(timeout)  # Use a much longer timeout for large responses
        
        try:
            start_time = time.time()
            data_buffer = b''
            
            while True:
                try:
                    chunk = self.sock.recv(buffer_size)
                    if not chunk:
                        if not chunks:
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    data_buffer = b''.join(chunks)
                    total_bytes = len(data_buffer)
                    
                    # Try to parse what we have as JSON
                    try:
                        # If parsing succeeds, we have a complete response
                        json.loads(data_buffer.decode('utf-8'))
                        logger.debug(f"Received complete response ({total_bytes} bytes)")
                        return data_buffer
                    except json.JSONDecodeError:
                        # Check if we've received a large enough payload that might indicate
                        # we're dealing with image data
                        if total_bytes > 1000000:  # Over 1MB, likely a very large image
                            logger.info(f"Large data transfer in progress ({total_bytes} bytes so far)")
                        
                        # Not a complete JSON yet, continue if within timeout
                        elapsed = time.time() - start_time
                        if elapsed > timeout:
                            logger.warning(f"Timeout exceeded after receiving {total_bytes} bytes")
                            break
                        continue
                        
                except socket.timeout:
                    logger.warning(f"Socket timeout after receiving {len(data_buffer) if data_buffer else 0} bytes")
                    break
                    
                except (ConnectionError, BrokenPipeError) as e:
                    logger.error(f"Socket connection error: {str(e)}")
                    raise
                    
        except socket.timeout:
            logger.warning(f"Socket timeout during receive operation after {time.time() - start_time:.2f}s")
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        # Try to use what we have
        if chunks:
            data_buffer = b''.join(chunks)
            total_bytes = len(data_buffer)
            try:
                # Try to parse what we have
                parsed_data = json.loads(data_buffer.decode('utf-8'))
                return data_buffer
            except json.JSONDecodeError as e:
                # Check if we received a large amount of data that might be a partial base64 image
                if total_bytes > 100000:  # Over 100KB, likely containing image data
                    logger.warning(f"Received large incomplete JSON ({total_bytes} bytes), likely containing image data")
                    # Try to fix common issues with base64 image data
                    try:
                        # Sometimes the JSON might be malformed at the end - try to recover
                        data_str = data_buffer.decode('utf-8', errors='replace')
                        
                        # First attempt: Find the end of the base64 string
                        first_quote_pos = data_str.find('"image_base64": "') + 16
                        if first_quote_pos > 16:  # Found the start of base64 data
                            second_quote_pos = data_str.find('"', first_quote_pos)
                            if second_quote_pos == -1:  # End quote not found, fix by adding it
                                # Find the last valid closing structure
                                possible_end = data_str.rfind('"}')
                                if possible_end > first_quote_pos:
                                    # Attempt to reconstruct a valid JSON by adding closing quote and brace
                                    repaired_json = data_str[:possible_end+2]
                                    # Try parsing the patched JSON
                                    try:
                                        json.loads(repaired_json)
                                        logger.info(f"Successfully recovered JSON by reconstructing it")
                                        return repaired_json.encode('utf-8')
                                    except:
                                        pass
                                        
                        # Second attempt: Look for common JSON structural elements at the end
                        for end_marker in ['}}', '"}}', '"}]}', '"}}}']:
                            last_pos = data_str.rfind(end_marker)
                            if last_pos > 0:
                                truncated_data = data_str[:last_pos + len(end_marker)]
                                try:
                                    # Try parsing the truncated data
                                    json.loads(truncated_data)
                                    logger.info(f"Successfully recovered JSON by truncating at marker {end_marker}")
                                    return truncated_data.encode('utf-8')
                                except:
                                    pass
                                    
                        # Third attempt: Extract just the first object level
                        # This extracts the status and removes image_base64 that might be corrupted
                        if '"status": "success"' in data_str and '"result":' in data_str:
                            try:
                                # Build a minimally viable response removing the image data
                                minimal_json = '{' + data_str.split('"status": "success"')[0] + '"status": "success", "result": {"status": "success", "image_truncated": true}}'
                                json.loads(minimal_json)
                                logger.info("Generated minimal success response, removed image data")
                                return minimal_json.encode('utf-8')
                            except:
                                pass
                    except Exception as repair_err:
                        logger.error(f"Failed to repair JSON: {str(repair_err)}")
                
                # Still unable to parse, provide detailed error
                data_preview = data_buffer.decode('utf-8', errors='replace')[:200] + "..." if len(data_buffer) > 200 else data_buffer.decode('utf-8', errors='replace')
                logger.error(f"Incomplete JSON response ({total_bytes} bytes): {data_preview}")
                
                # For very large responses, return a substitute response instead of failing
                if total_bytes > 200000:  # Over 200KB, definitely an image
                    logger.info("Creating substitute response for large image data")
                    substitute_response = {
                        "status": "success", 
                        "result": {
                            "status": "partial_success", 
                            "message": f"Received {total_bytes} bytes of data but JSON was incomplete. Image data was too large to process.",
                            "image_received": True,
                            "image_size": total_bytes,
                            "filepath": data_str.split('"filepath": "')[1].split('"')[0] if '"filepath": "' in data_str else "unknown"
                        }
                    }
                    return json.dumps(substitute_response).encode('utf-8')
                
                raise Exception(f"Incomplete JSON response received ({total_bytes} bytes, error at position {e.pos})")
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

