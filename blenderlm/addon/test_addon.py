# test_addon.py
# Script to test BlenderLM add-on and server startup in Blender headless mode
import bpy # type: ignore
import sys
import os

# Path to the addon (adjust if needed)
ADDON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "blenderlm_addon.py"))

# Dynamically load the add-on module
if ADDON_PATH not in sys.path:
    sys.path.append(os.path.dirname(ADDON_PATH))

import blenderlm_addon

# Register the add-on and start the server
blenderlm_addon.register()
port = 9876
bpy.types.blenderlm_server = blenderlm_addon.BlenderLMServer(port=port)
bpy.types.blenderlm_server.start()
bpy.context.scene.blenderlm_server_running = True
print(f"[TEST] BlenderLM server started on port {port}")

# Keep Blender running for a short period to allow connection tests
import time
try:
    print("[TEST] BlenderLM server running for 10 seconds...")
    time.sleep(10)
except KeyboardInterrupt:
    print("[TEST] Interrupted by user.")
finally:
    print("[TEST] Stopping BlenderLM server...")
    bpy.types.blenderlm_server.stop()
    print("[TEST] BlenderLM server stopped.")
