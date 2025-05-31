# import os
# import google.generativeai as genai
# import google.ai.generativelanguage as glm
# from PIL import Image
# from typing import AsyncGenerator, List, Optional, Callable, Dict
# import json

# from ._base_agent import BaseAgent, AgentMessage, AgentTask

# class GeminiAgent(BaseAgent):
#     """
#     An agent that uses the Google Gemini models via the google-generativeai SDK.
#     Supports multimodal input (text and images) and automatic function calling.
#     Tool functions should be provided during initialization.
#     """

#     def __init__(
#         self,
#         tools: List[Callable],
#         model_name: str = "gemini-1.5-flash-latest",
#         api_key: Optional[str] = os.environ.get("GEMINI_API_KEY")
#     ):
#         """
#         Initializes the GeminiAgent.

#         Args:
#             tools: A list of callable functions (async) that the agent can use.
#                    These should be compatible with Gemini's automatic function calling.
#             model_name: The name of the Gemini model to use.
#             api_key: Google API key. If None, it's assumed to be configured
#                      via environment variables (GOOGLE_API_KEY) or other means.
#         """
#         if api_key:
#             genai.configure(api_key=api_key)
#         else:
#             if not os.environ.get("GOOGLE_API_KEY"):
#                 print("Warning: No API key provided directly or found in GOOGLE_API_KEY environment variable. Ensure google.generativeai is configured elsewhere.")

#         # Store tool list and create a map for execution lookup
#         self.tools_list = tools if tools else []
#         self.tool_map: Dict[str, Callable] = {}
#         if self.tools_list:
#             for tool_func in self.tools_list:
#                 if hasattr(tool_func, '__name__'):
#                     self.tool_map[tool_func.__name__] = tool_func
#                 else:
#                     # Handle tools without __name__ (e.g., functools.partial)
#                     print(f"Warning: Tool {tool_func} might not be callable by name via function calling.")
#         else:
#              print("Warning: No tools provided during GeminiAgent initialization.")

#         # Initialize the model. Tools will be passed during generate calls.
#         self.model = genai.GenerativeModel(model_name)

#     def _task_to_gemini_contents(self, task: AgentTask) -> List[glm.Content]:
#         """Converts the AgentTask into the Gemini API's content format."""
#         contents = []
#         if isinstance(task, str):
#             contents.append(glm.Part(text=task))
#         elif isinstance(task, list):
#             for item in task:
#                 if isinstance(item, str):
#                     contents.append(glm.Part(text=item))
#                 elif isinstance(item, Image.Image):
#                     contents.append(item)
#                 else:
#                     print(f"Warning: Unsupported type in task list: {type(item)}. Skipping.")
#         else:
#             raise TypeError(f"Unsupported task type: {type(task)}")
#         # Return a list containing one Content object for the initial user message
#         return [glm.Content(parts=contents, role="user")]

#     async def run(self, task: AgentTask) -> AgentMessage:
#         """
#         Runs the agent with the given task, manually handling function execution.
#         """
#         history = self._task_to_gemini_contents(task) # Initial user message

#         try:
#             # --- First API Call --- 
#             print("Sending initial request to Gemini...")
#             response = await self.model.generate_content_async(
#                 contents=history, # Send initial user prompt
#                 tools=self.tools_list, # Declare available tools
#             )
#             print("Received initial response from Gemini.")

#             # Check for function call request in the first response
#             response_candidate = response.candidates[0] if response.candidates else None
#             response_part = response_candidate.content.parts[0] if response_candidate and response_candidate.content.parts else None
#             tool_calls_requested = [] # Keep track of requested calls for metadata

#             # --- Manual Function Execution Loop --- 
#             while response_part and response_part.function_call:
#                 function_call = response_part.function_call
#                 tool_name = function_call.name
#                 tool_args = dict(function_call.args) # Convert proto Map to dict
#                 tool_calls_requested.append(function_call) # Store the request

#                 print(f"Tool call requested: {tool_name}({tool_args})")

#                 # Add the model's request (function call) to history
#                 if response_candidate and response_candidate.content:
#                     history.append(response_candidate.content)

#                 # --- Execute the Tool --- 
#                 if tool_name in self.tool_map:
#                     tool_func = self.tool_map[tool_name]
#                     tool_result_data = None
#                     try:
#                         print(f"Executing tool: {tool_name} with args: {tool_args}")
#                         # Execute the function (assuming it's async)
#                         tool_result = await tool_func(**tool_args)

#                         # Format result for API (must be JSON serializable dict)
#                         if isinstance(tool_result, (str, int, float, bool, list, dict, type(None))):
#                             tool_result_data = {"result": tool_result}
#                         else:
#                             # Attempt to convert complex objects
#                             try:
#                                 # If the tool returns a dict, use it directly
#                                 if isinstance(tool_result, dict):
#                                      tool_result_data = tool_result
#                                 else:
#                                      # Try JSON serialization or fallback to string
#                                      tool_result_data = {"result": json.loads(json.dumps(tool_result))}
#                             except (TypeError, json.JSONDecodeError):
#                                 tool_result_data = {"result": str(tool_result)} # Fallback
                        
#                         print(f"Tool {tool_name} executed successfully.")

#                     except Exception as tool_error:
#                         print(f"Error executing tool {tool_name}: {tool_error}")
#                         tool_result_data = {"error": str(tool_error)} # Send error back to model

#                     # --- Prepare Function Response for API --- 
#                     function_response_part = glm.Part(
#                         function_response=glm.FunctionResponse(
#                             name=tool_name,
#                             response=tool_result_data # API expects a dict
#                         )
#                     )
#                     # Add the function response to history
#                     history.append(glm.Content(parts=[function_response_part], role="function"))

#                     # --- Second (or subsequent) API Call --- 
#                     print("Sending tool result back to model...")
#                     response = await self.model.generate_content_async(
#                         contents=history, # Send updated history
#                         tools=self.tools_list, # Redeclare tools
#                     )
#                     print("Received response after sending tool result.")
#                     # Update response candidate and part for the next loop iteration or final processing
#                     response_candidate = response.candidates[0] if response.candidates else None
#                     response_part = response_candidate.content.parts[0] if response_candidate and response_candidate.content.parts else None

#                 else:
#                     print(f"Error: Tool '{tool_name}' requested by model not found.")
#                     # Stop the loop and return an error message
#                     return AgentMessage(
#                         content=f"Error: Requested tool '{tool_name}' is not available.",
#                         role="assistant",
#                         metadata={
#                             "error": "Tool not found", 
#                             "tool_name": tool_name,
#                             "finish_reason": response_candidate.finish_reason.name if response_candidate else None,
#                             "usage": response.usage_metadata if hasattr(response, 'usage_metadata') else None,
#                             "raw_response": response
#                             }
#                     )
#             # --- End of Manual Function Execution Loop --- 

#             # --- Process the final response (after loop completes or if no tool call initially) ---
#             final_content = None
#             metadata = {
#                 "finish_reason": response_candidate.finish_reason.name if response_candidate else None,
#                 "usage": response.usage_metadata if hasattr(response, 'usage_metadata') else None,
#                 "raw_response": response, # Store the *final* raw response
#                 "tool_calls_requested": tool_calls_requested # Include the tool calls that were requested
#             }

#             if response_candidate and response_part and not response_part.function_call: # Ensure it's text
#                  text_parts = [p.text for p in response_candidate.content.parts if hasattr(p, 'text')]
#                  if text_parts:
#                      final_content = " ".join(text_parts).strip()
#                  else:
#                      final_content = "" # No text parts found
#             elif not response_part:
#                  final_content = "" 
#                  print("Warning: Received empty or unexpected final response structure.")
#             elif response_part.function_call:
#                  # This case should ideally not be reached if the loop logic is correct
#                  # and the model eventually returns text, but handle defensively.
#                  final_content = "" 
#                  print("Warning: Final response was unexpectedly another function call after loop.")

#             return AgentMessage(
#                 content=final_content,
#                 role="assistant",
#                 tool_calls=None, # Final response is content, not a request
#                 metadata=metadata
#             )

#         except Exception as e:
#             print(f"Error during Gemini API interaction: {e}")
#             return AgentMessage(
#                 content=f"An error occurred during API interaction: {e}",
#                 role="assistant",
#                 metadata={"error": str(e)}
#             )

#     async def run_stream(self, task: AgentTask) -> AsyncGenerator[AgentMessage, None]:
#         """
#         Runs the agent with the given task and streams the response.
#         NOTE: Manual function calling loop is NOT implemented for streaming.
#         This will yield function call requests if the model returns them.
#         """
#         initial_user_message = self._task_to_gemini_contents(task)
#         try:
#             # Model is NOT configured with tools here for stream, pass them
#             stream = await self.model.generate_content_async(
#                 contents=initial_user_message,
#                 tools=self.tools_list, # Declare tools
#                 stream=True
#             )
#             async for chunk in stream:
#                 chunk_content = None
#                 chunk_tool_calls = None
#                 chunk_metadata = {}

#                 candidate = chunk.candidates[0] if chunk.candidates else None
#                 if candidate:
#                     chunk_metadata = {
#                         "finish_reason": candidate.finish_reason.name,
#                         "usage": chunk.usage_metadata if hasattr(chunk, 'usage_metadata') else None,
#                     }

#                     if candidate.content and candidate.content.parts:
#                         part = candidate.content.parts[0]
#                         if part.function_call:
#                             print(f"Stream yielded function call request: {part.function_call.name}. Manual execution required by caller.")
#                             chunk_tool_calls = [{"function_call": part.function_call}]
#                             yield AgentMessage(
#                                 content=None,
#                                 role="assistant",
#                                 tool_calls=chunk_tool_calls,
#                                 metadata=chunk_metadata
#                             )
#                             continue
#                         else:
#                             text_parts = [p.text for p in candidate.content.parts if hasattr(p, 'text')]
#                             if text_parts:
#                                 chunk_content = "".join(text_parts)

#                 if chunk_content:
#                     yield AgentMessage(
#                         content=chunk_content,
#                         role="assistant",
#                         tool_calls=None,
#                         metadata=chunk_metadata
#                     )

#         except Exception as e:
#             print(f"Error during Gemini streaming API call: {e}")
#             yield AgentMessage(
#                 content=f"An error occurred during streaming: {e}",
#                 role="assistant",
#                 metadata={"error": str(e)}
#             )
