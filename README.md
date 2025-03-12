# BlenderLM

BlenderLM is a Python package that enables LLMs (Large Language Models) to control and interact with Blender, the open-source 3D creation suite. It provides a clean API and tools designed specifically for use with LLM agent frameworks like Autogen.

## Features

- REST API for controlling Blender programmatically
- Ready-to-use Autogen tools for LLM agents
- Support for creating, modifying, and manipulating 3D objects
- Material and scene management
- Support for multiple client sessions

## Installation

```bash
# Install the base package
pip install blenderlm

# If you're using Autogen
pip install blenderlm[autogen]
```

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
blenderlm serve --port 8000
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

## Available Tools

BlenderLM provides the following tools:

- **Object Creation**: Create 3D primitives (cube, sphere, cylinder, etc.)
- **Object Manipulation**: Move, rotate, and scale objects
- **Material Management**: Create and apply materials
- **Scene Management**: Manage the 3D scene
- **Rendering**: Render the scene to an image

## License

MIT

## Acknowledgement

Inspired by [blencer-mcp](https://github.com/ahujasid/blender-mcp)
