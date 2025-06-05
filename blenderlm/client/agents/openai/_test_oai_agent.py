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