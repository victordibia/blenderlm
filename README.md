# BlenderLM

![BlenderLM Logo](https://raw.githubusercontent.com/yourusername/blenderlm/main/docs/icon.png)

[![PyPI version](https://badge.fury.io/py/blenderlm.svg)](https://pypi.org/project/blenderlm/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

BlenderLM is a Python package that enables LLMs (Large Language Models) to control and interact with Blender, the open-source 3D creation suite. It provides a clean API and tools designed specifically for use with LLM agent frameworks like Autogen.

## Features

- REST API for controlling Blender programmatically
- Ready-to-use Autogen tools for LLM agents
- Support for creating, modifying, and manipulating 3D objects
- Material and scene management
- Support for multiple client sessions
- Web UI for intuitive interaction (optional)

## Installation

```bash
# Install the base package
pip install blenderlm

# If you're using Autogen
pip install blenderlm[autogen]
```

## Architecture

BlenderLM consists of three main components:

1. **Blender Addon**: A Blender addon that exposes Blender functionality via a socket server
2. **API Server**: A FastAPI server that communicates with the Blender addon and provides a REST API
3. **Client Library**: Python client and tools for interacting with the API server (with Autogen integration)

## Blender Addon Setup

1. Install the BlenderLM addon in Blender:

   - Download the Blender addon file from the `addon` directory
   - In Blender, go to Edit > Preferences > Add-ons > Install
   - Select the downloaded file and click "Install Add-on"
   - Enable the addon by checking the box next to "Interface: BlenderLM"

2. Start the Blender addon server:
   - In Blender, go to the sidebar (N key)
   - Find the "BlenderLM" tab
   - Set the port (default: 9876)
   - Click "Start Server"

## Usage

### Starting the BlenderLM Server

```bash
# Start the server
blenderlm serve --port 8000 --blender-port 9876
```

### Quick Test

You can verify your setup with:

```bash
# Test connection to Blender
blenderlm test --check-only

# Run a simple test creating objects
blenderlm test
```

### Using with Autogen

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.models import OpenAIChatCompletionClient
from blenderlm.client import get_blender_tools

async def main():
    # Initialize the model client
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
    )

    # Get Blender tools
    blender_tools = await get_blender_tools(api_url="http://localhost:8000")

    # Create a Blender assistant agent
    blender_assistant = AssistantAgent(
        name="blender_assistant",
        description="A 3D modeling assistant that can create and manipulate objects in Blender",
        model_client=model_client,
        tools=blender_tools,
        system_message="""You are a 3D modeling assistant that can create and manipulate objects in Blender.
        Use the available Blender tools to help users create 3D scenes.
        Think step by step about what objects to create and how to position them.
        Provide clear explanations of what you're doing."""
    )

    # Now you can use this agent in your workflows
    # For example, in a group chat or directly
    await blender_assistant.run_stream(task="Create a simple scene with a red cube and a blue sphere")

asyncio.run(main())
```

### Get an Example Script

You can generate an example script with:

```bash
# Generate and display an example script
blenderlm example

# Save the example to a file
blenderlm example --output=my_script.py
```

## Direct API Usage

If you prefer to use the API directly:

```python
import httpx

async def create_scene():
    async with httpx.AsyncClient() as client:
        # Create a cube
        cube_response = await client.post(
            "http://localhost:8000/api/objects",
            json={
                "type": "CUBE",
                "name": "MyCube",
                "location": [0, 0, 0]
            }
        )
        cube = cube_response.json()

        # Set material for the cube
        await client.post(
            "http://localhost:8000/api/materials",
            json={
                "object_name": "MyCube",
                "color": [1.0, 0.0, 0.0, 1.0]  # Red
            }
        )

        # Create a sphere
        sphere_response = await client.post(
            "http://localhost:8000/api/objects",
            json={
                "type": "SPHERE",
                "name": "MySphere",
                "location": [2, 0, 0]
            }
        )

        # Set material for the sphere
        await client.post(
            "http://localhost:8000/api/materials",
            json={
                "object_name": "MySphere",
                "color": [0.0, 0.0, 1.0, 1.0]  # Blue
            }
        )
```

## Web UI (Optional)

BlenderLM includes an optional web UI for interactive control. The frontend is built with Gatsby and communicates with the BlenderLM API.

To start the web UI:

```bash
cd frontend
yarn install
yarn start
```

## Available Tools

BlenderLM provides the following tools:

- **Object Creation**: Create 3D primitives (cube, sphere, cylinder, etc.)
- **Object Manipulation**: Move, rotate, and scale objects
- **Material Management**: Create and apply materials
- **Scene Management**: Manage the 3D scene
- **Rendering**: Render the scene to an image

## Command Line Interface

```bash
# Show help
blenderlm --help

# Show version
blenderlm version

# Start the server
blenderlm serve --port 8000 --blender-port 9876

# Test connection
blenderlm test

# Generate example script
blenderlm example --output=my_script.py
```

## Security Note

The BlenderLM addon opens a socket server that accepts and executes commands. Only use it on trusted networks as it has no authentication mechanism by default.

## License

MIT

## Acknowledgement

Inspired by [blender-mcp](https://github.com/ahujasid/blender-mcp)
