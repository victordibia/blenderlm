import asyncio
import os
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional

import rich
import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from typing_extensions import Annotated
from .client import BlenderLMClient
from .version import VERSION

# Create Typer app
app = typer.Typer(
    name="blenderlm",
    help="Control Blender with LLM agents",
    add_completion=False,
)

# Create console for rich output
console = Console()


def print_banner():
    """Print a fancy banner for BlenderLM"""
    console.print(Panel.fit(
        f"[bold blue]BlenderLM[/bold blue] [white]v{VERSION}[/white]",
        subtitle="Control Blender with LLM agents",
        border_style="blue",
    ))


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8199,
    blender_host: str = "localhost",
    blender_port: int = 9876,
    log_level: str = "info",
    reload: Annotated[bool, typer.Option("--reload")] = False,
):
    """
    Start the BlenderLM API server.
    
    This server provides a REST API that allows LLM agents to control Blender.
    """
    print_banner()
    
    # Configuration for the server
    env_vars = {
        "BLENDERLM_HOST": host,
        "BLENDERLM_PORT": str(port),
        "BLENDERLM_BLENDER_HOST": blender_host,
        "BLENDERLM_BLENDER_PORT": str(blender_port),
    }
    
    # Create temporary env file to share configuration with uvicorn
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_env:
        env_file_path = temp_env.name
        for key, value in env_vars.items():
            temp_env.write(f"{key}={value}\n")
    
    # Display startup information
    console.print(f"[bold green]Starting BlenderLM API server:[/bold green]")
    console.print(f"• API server: [bold]http://{host}:{port}[/bold]")
    console.print(f"• Connecting to Blender on: [bold]{blender_host}:{blender_port}[/bold]")
    console.print(f"• Log level: [bold]{log_level}[/bold]")
    console.print()
    console.print("[yellow]Press Ctrl+C to stop the server[/yellow]")
    console.print()
    
    try:
        # Start the FastAPI server
        uvicorn.run(
            "blenderlm.server.app:app",
            host=host,
            port=port,
            log_level=log_level,
            reload=reload,
            env_file=env_file_path,
        )
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Server stopped[/bold yellow]")
    finally:
        # Clean up the temp file
        try:
            os.unlink(env_file_path)
        except:
            pass


@app.command()
def check(
    blender_host: str = "localhost",
    blender_port: int = 9876,
    timeout: int = 5,
):
    """
    Check if Blender is running and the addon is active.
    """
    print_banner()
    
    import socket
    import json
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Checking connection to Blender...[/bold blue]"),
        transient=True,
    ) as progress:
        task = progress.add_task("Checking...", total=None)
        
        # Try to connect to Blender
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((blender_host, blender_port))
            
            # Send a ping command
            command = json.dumps({"type": "ping"})
            sock.sendall(command.encode('utf-8'))
            
            # Wait for response
            response = sock.recv(1024)
            result = json.loads(response.decode('utf-8'))
            
            progress.stop()
            
            if result.get("status") == "success":
                console.print("[bold green]✓ Blender is running and the addon is active![/bold green]")
                
                # Try to get more information
                try:
                    command = json.dumps({"type": "get_simple_info"})
                    sock.sendall(command.encode('utf-8'))
                    response = sock.recv(1024)
                    info = json.loads(response.decode('utf-8')).get("result", {})
                    
                    table = Table(title="Blender Information")
                    table.add_column("Property", style="cyan")
                    table.add_column("Value", style="green")
                    
                    if "blender_version" in info:
                        table.add_row("Blender Version", info["blender_version"])
                    if "scene_name" in info:
                        table.add_row("Scene Name", info["scene_name"])
                    if "object_count" in info:
                        table.add_row("Object Count", str(info["object_count"]))
                    
                    console.print(table)
                except:
                    pass
            else:
                console.print("[bold red]✗ Blender responded but the addon might not be working correctly[/bold red]")
                
            sock.close()
            
        except socket.timeout:
            progress.stop()
            console.print("[bold red]✗ Connection timed out[/bold red]")
            console.print("\nMake sure Blender is running and the BlenderLM addon is active.")
            console.print("In Blender, go to the sidebar (press N) and check the BlenderLM tab.")
            return 1
        except ConnectionRefusedError:
            progress.stop()
            console.print("[bold red]✗ Connection refused[/bold red]")
            console.print("\nMake sure Blender is running and the BlenderLM addon is active.")
            console.print("In Blender, go to the sidebar (press N) and check the BlenderLM tab.")
            return 1
        except Exception as e:
            progress.stop()
            console.print(f"[bold red]✗ Error: {str(e)}[/bold red]")
            return 1
    
    return 0


@app.command()
def example(output: Optional[Path] = None):
    """
    Generate an example script using BlenderLM with Autogen.
    """
    print_banner()
    
    example_code = '''
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

    # Start the conversation
    await blender_assistant.run_stream(
        task="Create a simple snow person with a carrot nose"
    )

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    if output:
        # Write to file
        with open(output, 'w') as f:
            f.write(example_code.strip())
        console.print(f"[bold green]Example script written to:[/bold green] {output}")
    else:
        # Print to console
        console.print("[bold green]Example Script:[/bold green]")
        console.print(Panel(example_code.strip(), border_style="green"))
        console.print("\n[yellow]To save this script to a file, use:[/yellow]")
        console.print("blenderlm example --output=my_script.py")


@app.command()
def install():
    """
    Install the BlenderLM addon to Blender.
    
    This will locate your Blender installation and copy the addon files.
    """
    print_banner()
    
    console.print("[bold yellow]⚠️ This feature is not yet implemented[/bold yellow]")
    console.print("\nFor now, please manually install the addon:")
    console.print("1. Navigate to the 'addon' directory in the BlenderLM package")
    console.print("2. In Blender, go to Edit > Preferences > Add-ons > Install")
    console.print("3. Select the addon file and click Install Add-on")
    console.print("4. Enable the addon by checking the box")
    
    # Implementation would involve:
    # 1. Locating Blender's addon directory
    # 2. Copying the addon files
    # 3. Providing instructions to enable it


@app.command()
def run_script(
    script_path: Path,
    blender_host: str = "localhost",
    blender_port: int = 9876,
):
    """
    Run a Python script in Blender.
    
    This allows you to execute arbitrary Python code in the Blender environment.
    """
    print_banner()
    
    if not script_path.exists():
        console.print(f"[bold red]Error: Script not found:[/bold red] {script_path}")
        return 1
    
    # Read the script file
    try:
        with open(script_path, 'r') as f:
            script_code = f.read()
    except Exception as e:
        console.print(f"[bold red]Error reading script:[/bold red] {str(e)}")
        return 1
    
    # Connect to Blender and run the script
    import socket
    import json
    
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]Running script in Blender...[/bold blue]"),
        transient=True,
    ) as progress:
        task = progress.add_task("Running...", total=None)
        
        try:
            # Connect to Blender
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((blender_host, blender_port))
            
            # Send the execute_code command
            command = json.dumps({
                "type": "execute_code",
                "params": {"code": script_code}
            })
            sock.sendall(command.encode('utf-8'))
            
            # Receive response
            chunks = []
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    
                    # Try to parse what we have
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        # If parsing succeeded, we have a complete response
                        break
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    break
            
            response_data = b''.join(chunks)
            response = json.loads(response_data.decode('utf-8'))
            
            progress.stop()
            
            if response.get("status") == "success":
                console.print("[bold green]✓ Script executed successfully![/bold green]")
                if "result" in response:
                    console.print("\n[bold]Result:[/bold]")
                    console.print(response["result"])
            else:
                console.print("[bold red]✗ Error executing script[/bold red]")
                if "message" in response:
                    console.print(f"\n[red]{response['message']}[/red]")
                    
            sock.close()
            
        except socket.timeout:
            progress.stop()
            console.print("[bold red]✗ Connection timed out[/bold red]")
            console.print("\nMake sure Blender is running and the BlenderLM addon is active.")
            return 1
        except ConnectionRefusedError:
            progress.stop()
            console.print("[bold red]✗ Connection refused[/bold red]")
            console.print("\nMake sure Blender is running and the BlenderLM addon is active.")
            return 1
        except Exception as e:
            progress.stop()
            console.print(f"[bold red]✗ Error: {str(e)}[/bold red]")
            return 1
    
    return 0


@app.command()
def version():
    """
    Show the BlenderLM version.
    """
    console.print(f"BlenderLM version: [bold blue]{VERSION}[/bold blue]")

@app.command()
def test(
    api_url: str = "http://localhost:8199",
    blender_host: str = "localhost",
    blender_port: int = 9876,
    check_only: bool = False,
):
    """
    Test the BlenderLM setup by creating objects in Blender.
    
    This command will connect to the API server and create test objects
    to verify that the entire pipeline is working correctly.
    """
    print_banner()
    
    console = Console()
    
    # First check if Blender is running with the addon
    if check_blender_connection(console, blender_host, blender_port) != 0:
        return 1
    
    # If check_only flag is set, don't proceed with creating objects
    if check_only:
        console.print("[green]Blender connection verified. Use without --check-only to run the full test.[/green]")
        return 0
    
    # Run the test
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Running BlenderLM test...[/bold blue]"),
        transient=True,
    ) as progress:
        task = progress.add_task("Testing...", total=None)
        
        try:
            # Run the client test
            client = BlenderLMClient(api_url=api_url)
            result = asyncio.run(client.run_test_scene())
            
            progress.stop()
            
            if "failed" in result.lower():
                console.print(f"[bold red]✗ Test failed[/bold red]")
                console.print(f"[red]{result}[/red]")
                return 1
            else:
                console.print("[bold green]✓ Test completed successfully![/bold green]")
                console.print(f"[green]{result}[/green]")
                
                console.print("\n[bold]Check Blender to see the created objects:[/bold]")
                console.print("• A red cube at position [-1, 0, 0]")
                console.print("• A blue cube at position [1, 0, 0]")
                return 0
                
        except Exception as e:
            progress.stop()
            console.print(f"[bold red]✗ Test failed with error:[/bold red]")
            console.print(f"[red]{str(e)}[/red]")
            return 1


def check_blender_connection(console, host, port):
    """Check if Blender is running with the addon activated"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Checking connection to Blender...[/bold blue]"),
        transient=True,
    ) as progress:
        task = progress.add_task("Checking...", total=None)
        
        import socket
        import json
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            
            # Send a ping command
            command = json.dumps({"type": "ping"})
            sock.sendall(command.encode('utf-8'))
            
            # Wait for response
            response = sock.recv(1024)
            result = json.loads(response.decode('utf-8'))
            
            progress.stop()
            
            if result.get("status") == "success":
                console.print("[bold green]✓ Blender is running and the addon is active![/bold green]")
                sock.close()
                return 0
            else:
                console.print("[bold red]✗ Blender responded but the addon might not be working correctly[/bold red]")
                sock.close()
                return 1
                
        except socket.timeout:
            progress.stop()
            console.print("[bold red]✗ Connection timed out[/bold red]")
            console.print("\nMake sure Blender is running and the BlenderLM addon is active.")
            return 1
        except ConnectionRefusedError:
            progress.stop()
            console.print("[bold red]✗ Connection refused[/bold red]")
            console.print("\nMake sure Blender is running and the BlenderLM addon is active.")
            return 1
        except Exception as e:
            progress.stop()
            console.print(f"[bold red]✗ Error: {str(e)}[/bold red]")
            return 1

if __name__ == "__main__":
    app()