# BlenderLM

<img src="https://raw.githubusercontent.com/victordibia/blenderlm/main/docs/icon.png" width="100" height="100" alt="BlenderLM Logo" style="padding-bottom: 10px;">

<!-- [![PyPI version](https://badge.fury.io/py/blenderlm.svg)](https://pypi.org/project/blenderlm/) -->

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

BlenderLM is a Python sample app that enables LLMs (Large Language Models) to control and interact with Blender, the open-source 3D creation suite. It provides a clean API and tools designed specifically for use with LLM agent frameworks like Autogen/GoogleADK/CrewAI.

## Features

- REST API for controlling Blender programmatically
- Ready-to-use tools for LLM agents
- Support for creating, modifying, and manipulating 3D objects
- Material and scene management
- Web UI for intuitive interaction (optional)

## Installation

```bash
# Install the base package
pip install blenderlm
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

### Interacting with BlenderLM

You can interact with BlenderLM using the provided client library. Below is an example of how to create a simple agent that uses BlenderLM tools to create a 3D object in Blender.

```python
import asyncio
from blenderlm.client.agents import OpenAIAgent
from blenderlm.client import get_blender_tools
from blenderlm.client.agents import AgentMessage

async def main():
    blender_tool_functions = await get_blender_tools()

    # Instantiate the agent, passing the tool functions
    agent = OpenAIAgent(
        tools=blender_tool_functions,
        model_name="gpt-4.1-mini",
    )

    updates =   agent.run_stream(
        task="Create a low poly well with the right materials and colors.",
    )
    async for update in updates:
        if isinstance(update, AgentMessage):
            print(update.role,":", update.content, str(update.metadata))
        else:
            print(update.role,":", update.content)

if __name__ == "__main__":
    asyncio.run(main())

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

```

## Security Note

The BlenderLM addon opens a socket server that accepts and executes commands. Only use it on trusted networks as it has no authentication mechanism by default.

## License

MIT

## Acknowledgement

Inspired by [blender-mcp](https://github.com/ahujasid/blender-mcp)
