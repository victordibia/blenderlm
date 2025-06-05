import os
import json
import time
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import AsyncOpenAI

from .._base_agent import BaseAgentMessage, AgentEventMessage, AgentMessageMetadata, PlanMessage, Plan, PlanStep
from ._oai_utils import get_blender_scene_state


class PlannerAgent:
    """
    An agent specialized in breaking down complex Blender tasks into manageable, sequential steps.
    Uses structured output to ensure high-quality, actionable plans.
    """

    def __init__(
        self,
        model_name: str = "gpt-4.1",
        api_key: Optional[str] = None
    ):
        """Initialize the planner agent."""
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name

    async def plan(self, task: str) -> PlanMessage:
        """
        Create a detailed plan for accomplishing a Blender task, using current Blender scene context.
        
        Args:
            task: The user's Blender task description
            
        Returns:
            A PlanMessage object containing the plan with metadata
        """
        start_time = time.time()

        # Fetch Blender scene state for context
        scene_state = await get_blender_scene_state()

        planning_prompt = f"""
You are a senior Blender TD and Python automation engineer.
Design a concise execution plan where **each step equals one cohesive Python script** built with the Blender API.

BEST PRACTICES TO FOLLOW:
• Add a ground plane for proper object placement and shadows
• Implement proper 3-point lighting (key, fill, rim) or area lighting setup
• Position objects with correct spatial relationships (table tops above legs, etc.)
• Use appropriate materials and textures (wood texture for wooden objects, metal for metallic ones)
• Batch related operations (create object + material + texture in one step)
• Set proper camera angles and composition for the scene
• Consider scene hierarchy and organization for maintainability

TASK: {task}

PLANNING DIRECTIVES
===================
1. One-Module Rule  
   A single step must cover a full, self-contained chunk of functionality that sensibly lives in **one Python module / function**.  
   If you can `import` and call it as one unit, it is one step.

2. Object-Level Granularity  
   • Create a complete star, barrel, house, car, tree → 1 step each  
   • Never split an object into primitive operations (e.g., “add cylinder”, “bevel edges”).

3. System-Level Granularity  
   • Lighting rig, camera setup, world/environment, physics simulation → 1 step each  
   • Material libraries that apply to several related objects → 1 step.

4. Distinct Domains Only  
   Separate steps only when they belong to clearly different domains or when a later step depends on the output of an earlier one.

5. No Micro-Steps (WRONG)  
   ❌ “Create cylinder for barrel body”  
   ❌ “Extrude star points”  
   ❌ “Apply wood texture”

6. Example Granularity
   ✅ **Simple Scene**: "Create a medieval castle"
   • Step 1: "Set up scene environment with ground plane, lighting rig, and camera positioning"
   • Step 2: "Create complete castle structure with walls, towers, gates, and stone materials"
   
   ✅ **Kitchen Scene**: "Create a modern kitchen"
   • Step 1: "Set up kitchen environment with proper lighting and camera angles"
   • Step 2: "Create wooden dining table with matching chairs and wood textures"
   • Step 3: "Create kitchen appliances (refrigerator, stove, microwave) with metallic materials"
   • Step 4: "Add kitchen cabinets and countertops with appropriate materials"
   
   ✅ **Nature Scene**: "Create a forest clearing"
   • Step 1: "Set up outdoor environment with ground, sky, and natural lighting"
   • Step 2: "Create diverse tree collection with bark textures and foliage materials"
   • Step 3: "Add undergrowth, rocks, and forest floor details with nature materials"
   
   ✅ **Animation Setup**: "Create bouncing ball animation"
   • Step 1: "Set up scene with ground plane, lighting, and camera for animation"
   • Step 2: "Create ball with rubber material and physics-based bouncing animation"

7. Quality Guidelines
   • Always include scene fundamentals (ground, lighting, camera) as the first step
   • Group related objects by material/theme (all wooden furniture together)
   • Consider object hierarchy and proper spatial relationships
   • Batch materials, textures, and positioning with object creation
   • Ensure each step produces a visually complete, testable result
   
OUTPUT FORMAT
-------------
Return a JSON object that matches the Plan schema:
{{
  "steps": [
    {{
      "task": "<one-sentence step summary>",
      "reasoning": "<why this is a separate functional unit>"
    }},
    ...
  ]
}}

Think like a programmer first and an artist second. Produce the smallest set of high-impact steps that fully accomplish the task.
"""

        response = await self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {
                    "role": "system", 
                    "content":  planning_prompt
                },
                scene_state,
                
            ],
            response_format=Plan,
            temperature=0.1  # Lower temperature for more consistent planning
        )
        
        if not response.choices[0].message.parsed:
            raise ValueError("Failed to generate a valid plan")
        
        # Create PlanMessage with metadata
        duration = time.time() - start_time
        plan_obj = response.choices[0].message.parsed
        
        # Calculate usage metadata if available
        usage_dict = None
        if hasattr(response, 'usage') and response.usage:
            usage_dict = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        metadata = AgentMessageMetadata(
            usage=usage_dict,
            duration=duration,
            finish_reason="plan_generated"
        )
        
        # Create formatted content for UI display
        plan_content = f"📋 **EXECUTION PLAN FOR:** {task}\n\n"
        # plan_content += f"**Total Steps:** {len(plan_obj.steps)}\n\n"
        
        # for i, step in enumerate(plan_obj.steps, 1):
        #     plan_content += f"**Step {i}:**\n"
        #     plan_content += f"**Task:** {step.task}\n"
        #     plan_content += f"**Reasoning:** {step.reasoning}\n"
        #     plan_content += "\n---\n\n"
        
        return PlanMessage(
            plan=plan_obj,
            content=plan_content,
            role="assistant",
            metadata=metadata
        )

    def create_plan_event(self, plan_message: PlanMessage) -> BaseAgentMessage:
        """
        Create a nicely formatted event message for the UI to display the plan.
        Since PlanMessage already contains formatted content, we can use it directly
        or return it as is.
        """
        # The PlanMessage already contains formatted content, so we can return it directly
        # or create an event message with the same content for backwards compatibility
        return AgentEventMessage(
            content=plan_message.content,
            role="assistant",
            event_type="task_plan",
            metadata=plan_message.metadata
        )
