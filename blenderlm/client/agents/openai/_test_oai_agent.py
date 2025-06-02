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
        instructions="You are a helpful blender agent. You must ONLY USE the `execute_code` tool to address ALL of the user's requests. Importantly, you should consider that the final result of the code execution will be a rendered image, hence, where possible ensure that the camera is positioned to capture the intended view. Please use reasonable names for objects and materials to ensure we can referecence them meaningfully in future requests. At the beginning of the task, you will be given a list of objects in the scene and an snapshot of the current blender viewport (not the rendered scene image). You should use this information to guide your actions, build on it towards addressing the user's request, and avoid unnecessary changes to the scene. If you need to add new objects, ensure they are named appropriately and positioned correctly in the scene.",
    )

    updates =   agent.run_stream(
        task="Create a low poly well with the right materials and colors and then add it to the scene. Add decent lighting and nice plane. Also add a little shed over the well and a barrel next to it.",
    )
    async for update in updates:
        if isinstance(update, AgentMessage): 
            print(update.role,":", update.content, str(update.metadata))
        else:
            print(update.role,":", update.content)

if __name__ == "__main__":
    asyncio.run(main())