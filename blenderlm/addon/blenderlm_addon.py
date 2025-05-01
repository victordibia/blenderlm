import bpy # type: ignore
import json
import threading
import socket
import time
from bpy.props import StringProperty, IntProperty # type: ignore

bl_info = {
    "name": "BlenderLM",
    "author": "BlenderLM",
    "version": (0, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > BlenderLM",
    "description": "Connect Blender to LLMs via API",
    "category": "Interface",
}

class BlenderLMServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.client = None
        self.buffer = b''  # Buffer for incomplete data
    
    def start(self):
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.socket.setblocking(False)
            # Register the timer
            bpy.app.timers.register(self._process_server, persistent=True)
            print(f"BlenderLM server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to start server: {str(e)}")
            self.stop()
            
    def stop(self):
        self.running = False
        if hasattr(bpy.app.timers, "unregister"):
            if bpy.app.timers.is_registered(self._process_server):
                bpy.app.timers.unregister(self._process_server)
        if self.socket:
            self.socket.close()
        if self.client:
            self.client.close()
        self.socket = None
        self.client = None
        print("BlenderLM server stopped")

    def _process_server(self):
        """Timer callback to process server operations"""
        if not self.running:
            return None  # Unregister timer
            
        try:
            # Accept new connections
            if not self.client and self.socket:
                try:
                    self.client, address = self.socket.accept()
                    self.client.setblocking(False)
                    print(f"Connected to client: {address}")
                except BlockingIOError:
                    pass  # No connection waiting
                except Exception as e:
                    print(f"Error accepting connection: {str(e)}")
                
            # Process existing connection
            if self.client:
                try:
                    # Try to receive data
                    try:
                        data = self.client.recv(8192)
                        if data:
                            self.buffer += data
                            # Try to process complete messages
                            try:
                                # Attempt to parse the buffer as JSON
                                command = json.loads(self.buffer.decode('utf-8'))
                                # If successful, clear the buffer and process command
                                self.buffer = b''
                                response = self.execute_command(command)
                                
                                # Serialize response and send in chunks if large
                                response_json = json.dumps(response)
                                self._send_response_in_chunks(response_json)
                            except json.JSONDecodeError:
                                # Incomplete data, keep in buffer
                                pass
                        else:
                            # Connection closed by client
                            print("Client disconnected")
                            self.client.close()
                            self.client = None
                            self.buffer = b''
                    except BlockingIOError:
                        pass  # No data available
                    except Exception as e:
                        print(f"Error receiving data: {str(e)}")
                        self.client.close() if self.client else None
                        self.client = None
                        self.buffer = b''
                        
                except Exception as e:
                    print(f"Error with client: {str(e)}")
                    if self.client:
                        self.client.close()
                        self.client = None
                    self.buffer = b''
                    
        except Exception as e:
            print(f"Server error: {str(e)}")
            
        return 0.1  # Continue timer with 0.1 second interval
        
    def _send_response_in_chunks(self, response_json):
        """Send a JSON response in chunks if it's large"""
        if not self.client:
            return
            
        try:
            # Convert response to bytes
            response_bytes = response_json.encode('utf-8')
            total_size = len(response_bytes)
            
            # If response is small enough, send it all at once
            if total_size <= 16384:  # 16KB
                self.client.sendall(response_bytes)
                return
                
            # For large responses (like those with images), send in chunks
            print(f"Sending large response ({total_size} bytes) in chunks")
            chunk_size = 16384  # 16KB chunks
            
            # Set socket to blocking mode for reliable sending
            self.client.setblocking(True)
            
            # Send data in chunks
            for i in range(0, total_size, chunk_size):
                chunk = response_bytes[i:i + chunk_size]
                self.client.sendall(chunk)
                
            # Return to non-blocking mode after sending
            self.client.setblocking(False)
            print(f"Successfully sent large response of {total_size} bytes")
            
        except Exception as e:
            print(f"Error sending response: {str(e)}")
            import traceback
            traceback.print_exc()
            # Close the connection on error
            try:
                if self.client:
                    self.client.close()
                    self.client = None
            except:
                pass

    def execute_command(self, command):
        """Execute a command in the main Blender thread"""
        try:
            cmd_type = command.get("type")
            params = command.get("params", {})
            
            # Ensure we're in the right context
            if cmd_type in ["create_object", "modify_object", "delete_object"]:
                override = bpy.context.copy()
                override['area'] = [area for area in bpy.context.screen.areas if area.type == 'VIEW_3D'][0]
                with bpy.context.temp_override(**override):
                    return self._execute_command_internal(command)
            else:
                return self._execute_command_internal(command)
                
        except Exception as e:
            print(f"Error executing command: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _execute_command_internal(self, command):
        """Internal command execution with proper context"""
        cmd_type = command.get("type")
        params = command.get("params", {})

        # Add a simple ping handler
        if cmd_type == "ping":
            print("Handling ping command")
            return {"status": "success", "result": {"pong": True}}
        
        handlers = {
            "ping": lambda **kwargs: {"pong": True},
            "get_simple_info": self.get_simple_info,
            "get_scene_info": self.get_scene_info,
            "create_object": self.create_object,
            "modify_object": self.modify_object,
            "delete_object": self.delete_object,
            "get_object_info": self.get_object_info,
            "execute_code": self.execute_code,
            "set_material": self.set_material,
            "render_scene": self.render_scene,
            "capture_viewport": self.capture_viewport,
            "clear_scene": self.clear_scene,
            "add_camera": self.add_camera,
        }
        
        handler = handlers.get(cmd_type)
        if handler:
            try:
                print(f"Executing handler for {cmd_type}")
                result = handler(**params)
                print(f"Handler execution complete")
                return {"status": "success", "result": result}
            except Exception as e:
                print(f"Error in handler: {str(e)}")
                import traceback
                traceback.print_exc()
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": f"Unknown command type: {cmd_type}"}

    
    def get_simple_info(self):
        """Get basic Blender information"""
        return {
            "blender_version": ".".join(str(v) for v in bpy.app.version),
            "scene_name": bpy.context.scene.name,
            "object_count": len(bpy.context.scene.objects)
        }
    
    def get_scene_info(self):
        """Get information about the current Blender scene"""
        try:
            print("Getting scene info...")
            # Simplify the scene info to reduce data size
            scene_info = {
                "name": bpy.context.scene.name,
                "object_count": len(bpy.context.scene.objects),
                "objects": [],
                "materials_count": len(bpy.data.materials),
            }
            
            # Collect minimal object information
            for i, obj in enumerate(bpy.context.scene.objects):
                if i >= 20:  # Limit to 20 objects to avoid huge responses
                    break
                    
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    # Only include basic location data
                    "location": [round(float(obj.location.x), 2), 
                                round(float(obj.location.y), 2), 
                                round(float(obj.location.z), 2)],
                }
                scene_info["objects"].append(obj_info)
            
            print(f"Scene info collected: {len(scene_info['objects'])} objects")
            return scene_info
        except Exception as e:
            print(f"Error in get_scene_info: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def create_object(self, type="CUBE", name=None, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1), color=None):
        """Create a new object in the scene and optionally apply a color"""
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        
        # If name is provided and an object with that name already exists, delete it first
        if name and name in bpy.data.objects:
            obj_to_remove = bpy.data.objects[name]
            bpy.data.objects.remove(obj_to_remove, do_unlink=True)
        
        # Create the object based on type
        if type == "CUBE":
            bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation, scale=scale)
        elif type == "SPHERE":
            bpy.ops.mesh.primitive_uv_sphere_add(location=location, rotation=rotation, scale=scale)
        elif type == "CYLINDER":
            bpy.ops.mesh.primitive_cylinder_add(location=location, rotation=rotation, scale=scale)
        elif type == "PLANE":
            bpy.ops.mesh.primitive_plane_add(location=location, rotation=rotation, scale=scale)
        elif type == "CONE":
            bpy.ops.mesh.primitive_cone_add(location=location, rotation=rotation, scale=scale)
        elif type == "TORUS":
            bpy.ops.mesh.primitive_torus_add(location=location, rotation=rotation, scale=scale)
        elif type == "EMPTY":
            bpy.ops.object.empty_add(location=location, rotation=rotation, scale=scale)
        elif type == "CAMERA":
            bpy.ops.object.camera_add(location=location, rotation=rotation)
        elif type == "LIGHT":
            bpy.ops.object.light_add(type='POINT', location=location, rotation=rotation, scale=scale)
        else:
            raise ValueError(f"Unsupported object type: {type}")
        
        # Get the created object
        obj = bpy.context.active_object
        
        # Rename if name is provided
        if name:
            # First remove any existing object with the same name (already handled above)
            # Then set the name directly
            obj.name = name
            
            # In case there are linked data like mesh data with auto-naming,
            # also rename the data if it exists
            if hasattr(obj, 'data') and obj.data:
                obj.data.name = f"{name}_data"
        
        # Apply color if provided
        material_name = None
        if color and hasattr(obj, 'data') and hasattr(obj.data, 'materials'):
            try:
                mat_name = f"{obj.name}_material"
                mat = bpy.data.materials.get(mat_name)
                if not mat:
                    mat = bpy.data.materials.new(name=mat_name)
                
                # Set up material nodes
                mat.use_nodes = True
                principled = mat.node_tree.nodes.get('Principled BSDF')
                if not principled:
                    principled = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                    output = mat.node_tree.nodes.get('Material Output')
                    if not output:
                        output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
                    mat.node_tree.links.new(principled.outputs[0], output.inputs[0])
                
                # Set color
                if len(color) >= 3:
                    principled.inputs['Base Color'].default_value = (
                        color[0],
                        color[1],
                        color[2],
                        1.0 if len(color) < 4 else color[3]
                    )
                
                # Assign material to object
                if not obj.data.materials:
                    obj.data.materials.append(mat)
                else:
                    obj.data.materials[0] = mat
                
                material_name = mat.name
            except Exception as e:
                print(f"Error applying color: {str(e)}")
        
        return {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            "material": material_name
        }
    
    def modify_object(self, name, location=None, rotation=None, scale=None, visible=None):
        """Modify an existing object in the scene"""
        # Find the object by name
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        
        # Modify properties as requested
        if location is not None:
            obj.location = location
        
        if rotation is not None:
            obj.rotation_euler = rotation
        
        if scale is not None:
            obj.scale = scale
        
        if visible is not None:
            obj.hide_viewport = not visible
            obj.hide_render = not visible
        
        return {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            "visible": obj.visible_get(),
        }
    
    def delete_object(self, name):
        """Delete an object from the scene"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        
        # Store the name to return
        obj_name = obj.name
        
        # Select and delete the object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.delete()
        
        return {"deleted": obj_name}
    
    def get_object_info(self, name):
        """Get detailed information about a specific object"""
        obj = bpy.data.objects.get(name)
        if not obj:
            raise ValueError(f"Object not found: {name}")
        
        # Basic object info
        obj_info = {
            "name": obj.name,
            "type": obj.type,
            "location": [obj.location.x, obj.location.y, obj.location.z],
            "rotation": [obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z],
            "scale": [obj.scale.x, obj.scale.y, obj.scale.z],
            "visible": obj.visible_get(),
            "materials": [],
        }
        
        # Add material slots
        for slot in obj.material_slots:
            if slot.material:
                obj_info["materials"].append(slot.material.name)
        
        # Add mesh data if applicable
        if obj.type == 'MESH' and obj.data:
            mesh = obj.data
            obj_info["mesh"] = {
                "vertices": len(mesh.vertices),
                "edges": len(mesh.edges),
                "polygons": len(mesh.polygons),
            }
        
        return obj_info
    
    def execute_code(self, code):
        """Execute arbitrary Blender Python code"""
        # This is powerful but potentially dangerous - use with caution
        try:
            # Create a local namespace for execution
            namespace = {"bpy": bpy}
            exec(code, namespace)
            return {"executed": True}
        except Exception as e:
            raise Exception(f"Code execution error: {str(e)}")
    
    def set_material(self, object_name, material_name=None, create_if_missing=True, color=None):
        """Set or create a material for an object"""
        try:
            # Get the object
            obj = bpy.data.objects.get(object_name)
            if not obj:
                raise ValueError(f"Object not found: {object_name}")
            
            # Make sure object can accept materials
            if not hasattr(obj, 'data') or not hasattr(obj.data, 'materials'):
                raise ValueError(f"Object {object_name} cannot accept materials")
            
            # Create or get material
            if material_name:
                mat = bpy.data.materials.get(material_name)
                if not mat and create_if_missing:
                    mat = bpy.data.materials.new(name=material_name)
                    print(f"Created new material: {material_name}")
            else:
                # Generate unique material name if none provided
                mat_name = f"{object_name}_material"
                mat = bpy.data.materials.get(mat_name)
                if not mat:
                    mat = bpy.data.materials.new(name=mat_name)
                material_name = mat_name
                print(f"Using material: {mat_name}")
            
            # Set up material nodes if needed
            if mat:
                if not mat.use_nodes:
                    mat.use_nodes = True
                
                # Get or create Principled BSDF
                principled = mat.node_tree.nodes.get('Principled BSDF')
                if not principled:
                    principled = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                    # Get or create Material Output
                    output = mat.node_tree.nodes.get('Material Output')
                    if not output:
                        output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
                    # Link if not already linked
                    if not principled.outputs[0].links:
                        mat.node_tree.links.new(principled.outputs[0], output.inputs[0])
                
                # Set color if provided
                if color and len(color) >= 3:
                    principled.inputs['Base Color'].default_value = (
                        color[0],
                        color[1],
                        color[2],
                        1.0 if len(color) < 4 else color[3]
                    )
                    print(f"Set material color to {color}")
            
            # Assign material to object if not already assigned
            if mat:
                if not obj.data.materials:
                    obj.data.materials.append(mat)
                else:
                    # Only modify first material slot
                    obj.data.materials[0] = mat
                
                print(f"Assigned material {mat.name} to object {object_name}")


                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'VIEW_3D':
                            for region in area.regions:
                                if region.type == 'WINDOW':
                                    override = {'window': window, 'screen': window.screen, 'area': area, 'region': region}
                                    bpy.ops.wm.redraw_timer(override, type='DRAW_WIN_SWAP', iterations=1)

                
                return {
                    "status": "success",
                    "object": object_name,
                    "material": mat.name,
                    "color": color if color else None
                }
            else:
                raise ValueError(f"Failed to create or find material: {material_name}")
            
        except Exception as e:
            print(f"Error in set_material: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e),
                "object": object_name,
                "material": material_name if 'material_name' in locals() else None
            }

    def capture_viewport(self, filepath=None, camera_view=False, return_base64=True, max_dimension=1024):
        """Capture the current viewport content using OpenGL render and optionally return as base64"""
        try:
            # Generate a default filepath if none provided
            if not filepath:
                import tempfile
                import os
                temp_dir = tempfile.gettempdir()
                filepath = os.path.join(temp_dir, f"blenderlm_viewport_{int(time.time())}.png")
                
            # Ensure directory exists
            import os
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            # Store current render path
            original_path = bpy.context.scene.render.filepath
            
            # Set temporary render path
            bpy.context.scene.render.filepath = filepath
            
            # Switch to camera view if requested
            if camera_view:
                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        override = bpy.context.copy()
                        override['area'] = area
                        override['region'] = area.regions[-1]
                        bpy.ops.view3d.view_camera(override)
                        break
                        
            # Render viewport using OpenGL
            bpy.ops.render.opengl(write_still=True)
            
            # Restore original render path
            bpy.context.scene.render.filepath = original_path
            
            result = {
                "status": "success",
                "filepath": filepath
            }
            
            # Optionally encode the image as base64
            if return_base64 and os.path.exists(filepath):
                # Import PIL to resize images if needed
                try:
                    from PIL import Image
                    import base64
                    import io
                    
                    # Open and potentially resize the image before encoding
                    with Image.open(filepath) as img:
                        # Check if we need to resize
                        width, height = img.size
                        if width > max_dimension or height > max_dimension:
                            # Calculate new dimensions preserving aspect ratio
                            if width > height:
                                new_width = max_dimension
                                new_height = int(height * (max_dimension / width))
                            else:
                                new_height = max_dimension
                                new_width = int(width * (max_dimension / height))
                                
                            print(f"Resizing viewport image from {width}x{height} to {new_width}x{new_height}")
                            img = img.resize((new_width, new_height))
                            
                            # Save the resized image to a different path
                            resized_path = filepath.replace('.png', '_resized.png')
                            img.save(resized_path, 'PNG', optimize=True)
                            
                            # Replace filepath with resized path
                            result["original_path"] = filepath
                            result["filepath"] = resized_path
                            result["resized"] = True
                            result["original_size"] = [width, height]
                            result["new_size"] = [new_width, new_height]
                            
                            # Use the resized image for base64 encoding
                            filepath = resized_path
                        
                        # For base64 encoding, use a compressed format and memory buffer
                        buffer = io.BytesIO()
                        img.save(buffer, format="JPEG", quality=85, optimize=True)
                        buffer.seek(0)
                        image_data = buffer.read()
                        
                        # Calculate compression ratio for logs
                        orig_size = os.path.getsize(filepath)
                        compressed_size = len(image_data)
                        compression_ratio = (orig_size - compressed_size) / orig_size * 100
                        print(f"Compressed image from {orig_size} bytes to {compressed_size} bytes ({compression_ratio:.1f}% reduction)")
                        
                        # Encode the compressed image
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        result["image_base64"] = base64_data
                        result["compressed"] = True
                except ImportError:
                    # Fall back to regular file reading if PIL is not available
                    import base64
                    with open(filepath, 'rb') as image_file:
                        image_data = image_file.read()
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        result["image_base64"] = base64_data
                except Exception as img_err:
                    print(f"Error processing viewport image: {str(img_err)}")
                    result["image_error"] = str(img_err)
            
            return result
        except Exception as e:
            print(f"Error capturing viewport: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def render_scene(self, output_path=None, resolution_x=None, resolution_y=None, return_base64=True, max_dimension=1024):
        """Render the current scene"""
        try:
            if resolution_x is not None:
                bpy.context.scene.render.resolution_x = resolution_x
            
            if resolution_y is not None:
                bpy.context.scene.render.resolution_y = resolution_y
            
            # If no output path provided, create a temporary one
            if not output_path:
                import tempfile
                import os
                temp_dir = tempfile.gettempdir()
                output_path = os.path.join(temp_dir, f"blenderlm_render_{int(time.time())}.png")
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Store original path
            original_path = bpy.context.scene.render.filepath
            
            # Set render path
            bpy.context.scene.render.filepath = output_path
            
            # Render the scene
            bpy.ops.render.render(write_still=True)
            
            # Restore original path
            bpy.context.scene.render.filepath = original_path
            
            result = {
                "rendered": True,
                "output_path": output_path,
                "resolution": [bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y],
            }
            
            # Optionally encode the image as base64
            if return_base64 and os.path.exists(output_path):
                # Import PIL to resize images if needed
                try:
                    from PIL import Image
                    import base64
                    import io
                    
                    # Open and potentially resize the image before encoding
                    with Image.open(output_path) as img:
                        # Check if we need to resize
                        width, height = img.size
                        if width > max_dimension or height > max_dimension:
                            # Calculate new dimensions preserving aspect ratio
                            if width > height:
                                new_width = max_dimension
                                new_height = int(height * (max_dimension / width))
                            else:
                                new_height = max_dimension
                                new_width = int(width * (max_dimension / height))
                                
                            print(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
                            img = img.resize((new_width, new_height))
                            
                            # Save the resized image to a different path
                            resized_path = output_path.replace('.png', '_resized.png')
                            img.save(resized_path, 'PNG', optimize=True)
                            
                            # Replace output path with resized path
                            result["original_path"] = output_path
                            result["output_path"] = resized_path
                            result["resized"] = True
                            result["original_size"] = [width, height]
                            result["new_size"] = [new_width, new_height]
                            
                            # Use the resized image for base64 encoding
                            output_path = resized_path
                        
                        # For base64 encoding, use a compressed format and memory buffer
                        buffer = io.BytesIO()
                        img.save(buffer, format="JPEG", quality=85, optimize=True)
                        buffer.seek(0)
                        image_data = buffer.read()
                        
                        # Encode the compressed image
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        result["image_base64"] = base64_data
                        result["compressed"] = True
                except ImportError:
                    # Fall back to regular file reading if PIL is not available
                    import base64
                    with open(output_path, 'rb') as image_file:
                        image_data = image_file.read()
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        result["image_base64"] = base64_data
                except Exception as img_err:
                    print(f"Error processing image: {str(img_err)}")
                    result["image_error"] = str(img_err)
            
            return result
        except Exception as e:
            print(f"Error rendering scene: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e)
            }

    def clear_scene(self):
        """Clear all objects from the current scene"""
        try:
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete()
            return {"status": "success", "message": "Scene cleared"}
        except Exception as e:
            print(f"Error clearing scene: {str(e)}")
            return {"status": "error", "message": str(e)}

    def add_camera(self, location=(0, 0, 0), rotation=(0, 0, 0)):
        """Add a camera to the scene"""
        try:
            bpy.ops.object.camera_add(location=location, rotation=rotation)
            camera = bpy.context.active_object
            
            # Set this camera as the active camera for the scene
            bpy.context.scene.camera = camera
            
            return {
                "status": "success",
                "camera_name": camera.name,
                "location": [camera.location.x, camera.location.y, camera.location.z],
                "rotation": [camera.rotation_euler.x, camera.rotation_euler.y, camera.rotation_euler.z],
                "active": True
            }
        except Exception as e:
            print(f"Error adding camera: {str(e)}")
            return {"status": "error", "message": str(e)}

# Blender UI Panel
class BLENDERLM_PT_Panel(bpy.types.Panel):
    bl_label = "BlenderLM"
    bl_idname = "BLENDERLM_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderLM'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.prop(scene, "blenderlm_port")
        
        if not scene.blenderlm_server_running:
            layout.operator("blenderlm.start_server", text="Start Server")
        else:
            layout.operator("blenderlm.stop_server", text="Stop Server")
            layout.label(text=f"Running on port {scene.blenderlm_port}")
            layout.label(text="Connect API server to this port")

# Operator to start the server
class BLENDERLM_OT_StartServer(bpy.types.Operator):
    bl_idname = "blenderlm.start_server"
    bl_label = "Start BlenderLM Server"
    bl_description = "Start the BlenderLM server to connect with LLMs"
    
    def execute(self, context):
        scene = context.scene
        
        # Create a new server instance
        if not hasattr(bpy.types, "blenderlm_server") or not bpy.types.blenderlm_server:
            bpy.types.blenderlm_server = BlenderLMServer(port=scene.blenderlm_port)
        
        # Start the server
        bpy.types.blenderlm_server.start()
        scene.blenderlm_server_running = True
        
        return {'FINISHED'}

# Operator to stop the server
class BLENDERLM_OT_StopServer(bpy.types.Operator):
    bl_idname = "blenderlm.stop_server"
    bl_label = "Stop BlenderLM Server"
    bl_description = "Stop the BlenderLM server"
    
    def execute(self, context):
        scene = context.scene
        
        # Stop the server if it exists
        if hasattr(bpy.types, "blenderlm_server") and bpy.types.blenderlm_server:
            bpy.types.blenderlm_server.stop()
            del bpy.types.blenderlm_server
        
        scene.blenderlm_server_running = False
        
        return {'FINISHED'}

# Registration functions
def register():
    bpy.types.Scene.blenderlm_port = IntProperty(
        name="Port",
        description="Port for the BlenderLM server",
        default=9876,
        min=1024,
        max=65535
    )
    
    bpy.types.Scene.blenderlm_server_running = bpy.props.BoolProperty(
        name="Server Running",
        default=False
    )
    
    bpy.utils.register_class(BLENDERLM_PT_Panel)
    bpy.utils.register_class(BLENDERLM_OT_StartServer)
    bpy.utils.register_class(BLENDERLM_OT_StopServer)
    
    print("BlenderLM addon registered")

def unregister():
    # Stop the server if it's running
    if hasattr(bpy.types, "blenderlm_server") and bpy.types.blenderlm_server:
        bpy.types.blenderlm_server.stop()
        del bpy.types.blenderlm_server
    
    bpy.utils.unregister_class(BLENDERLM_PT_Panel)
    bpy.utils.unregister_class(BLENDERLM_OT_StartServer)
    bpy.utils.unregister_class(BLENDERLM_OT_StopServer)
    
    del bpy.types.Scene.blenderlm_port
    del bpy.types.Scene.blenderlm_server_running
    
    print("BlenderLM addon unregistered")

if __name__ == "__main__":
    register()