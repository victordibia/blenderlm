# BlenderLM Addon

This addon enables Blender to be controlled by Large Language Models (LLMs) through a socket server interface. It works in conjunction with the BlenderLM Python package.

## Installation

1. Download the `blenderlm_addon.py` file
2. Open Blender
3. Go to Edit > Preferences > Add-ons > Install
4. Select the downloaded `blenderlm_addon.py` file
5. Enable the addon by checking the box next to "Interface: BlenderLM"

## Usage

1. In Blender, open the sidebar (press N)
2. Find the "BlenderLM" tab
3. Set the port (default is 9876)
4. Click "Start Server"

The addon is now listening for commands from the BlenderLM API server.

## Connecting with BlenderLM

After starting the addon server in Blender, start the BlenderLM API server:

```bash
blenderlm serve --blender-port 9876
```

This will start the API server that LLM agents can use to control Blender.

## Security Note

This addon creates a socket server that executes commands in Blender. Only use it on trusted networks as it has no authentication mechanism.
