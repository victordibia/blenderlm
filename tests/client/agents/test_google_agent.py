\
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Assuming the structure allows this import. Adjust if necessary.
from blenderlm.client.agents._google_agent import GeminiAgent, AgentMessage
from blenderlm.client.client import BlenderLMClient # Need to import for mocking

# Mock the google generativeai library
# Create dummy classes/objects to mimic the structure expected by the agent
class MockPart:
    def __init__(self, text=None, function_call=None):
        if text is not None:
            self.text = text
        if function_call is not None:
            self.function_call = function_call
        # Add other attributes if needed by the code under test

class MockContent:
    def __init__(self, parts):
        self.parts = parts

class MockCandidate:
    def __init__(self, content, finish_reason_name="STOP"):
        self.content = content
        self.finish_reason = MagicMock()
        self.finish_reason.name = finish_reason_name

class MockGenAIResponse:
    def __init__(self, candidates, usage_metadata=None):
        self.candidates = candidates
        self.usage_metadata = usage_metadata or {"prompt_token_count": 5, "candidates_token_count": 10}

# Mock the genai module itself if direct calls like genai.configure are made
mock_genai = MagicMock()

class TestGeminiAgent(unittest.TestCase):

    @patch('blenderlm.client.agents._google_agent.genai', mock_genai) # Patch genai where it's imported
    def setUp(self):
        """Set up for test methods."""
        # Reset mocks for each test
        mock_genai.reset_mock()
        mock_genai.configure = MagicMock() # Mock configure

        # Mock the GenerativeModel instance and its async method
        self.mock_model_instance = MagicMock()
        self.mock_generate_content_async = AsyncMock()
        self.mock_model_instance.generate_content_async = self.mock_generate_content_async
        mock_genai.GenerativeModel.return_value = self.mock_model_instance

        # Mock BlenderLMClient
        self.mock_blender_client = MagicMock(spec=BlenderLMClient)
        self.mock_blender_client.get_tool_functions.return_value = [] # Assume no tools for basic test

        # Instantiate the agent with mocks
        # Provide a dummy API key to satisfy the constructor check
        self.agent = GeminiAgent(blender_client=self.mock_blender_client, api_key="fake_key")

    def test_run_simple_text_input(self):
        """Test the run method with a simple text prompt."""
        # Arrange
        test_prompt = "Hello, Gemini!"
        expected_response_text = "Hello there! This is a mocked response."

        # Configure the mock response from generate_content_async
        mock_response_part = MockPart(text=expected_response_text)
        mock_response_content = MockContent(parts=[mock_response_part])
        mock_response_candidate = MockCandidate(content=mock_response_content)
        mock_api_response = MockGenAIResponse(candidates=[mock_response_candidate])
        self.mock_generate_content_async.return_value = mock_api_response

        # Act
        # Run the async method using asyncio.run() for testing
        result_message = asyncio.run(self.agent.run(test_prompt))

        # Assert
        # 1. Check if genai.configure was called (usually in __init__)
        mock_genai.configure.assert_called_once_with(api_key="fake_key")

        # 2. Check if GenerativeModel was initialized
        mock_genai.GenerativeModel.assert_called_once_with(
            "gemini-1.5-flash-latest", # Default model
            # Add checks for safety_settings/generation_config if they were passed
        )

        # 3. Check if get_tool_functions was called
        self.mock_blender_client.get_tool_functions.assert_called_once()

        # 4. Check if generate_content_async was called correctly
        self.mock_generate_content_async.assert_awaited_once()
        call_args, call_kwargs = self.mock_generate_content_async.call_args
        self.assertEqual(len(call_kwargs['contents']), 1) # One part for simple text
        self.assertEqual(call_kwargs['contents'][0].text, test_prompt)
        self.assertEqual(call_kwargs['tools'], []) # Based on mock client

        # 5. Check the returned AgentMessage
        self.assertIsInstance(result_message, AgentMessage)
        self.assertEqual(result_message.content, expected_response_text)
        self.assertEqual(result_message.role, "assistant")
        self.assertIsNone(result_message.tool_calls)
        # Add checks for metadata existence before accessing keys
        self.assertIsNotNone(result_message.metadata)
        if result_message.metadata: # Type checker hint
            self.assertIn("finish_reason", result_message.metadata)
            self.assertEqual(result_message.metadata["finish_reason"], "STOP")
            self.assertIn("usage", result_message.metadata)
            self.assertEqual(result_message.metadata["usage"], mock_api_response.usage_metadata)

# Allow running the tests directly
if __name__ == '__main__':
    unittest.main()
