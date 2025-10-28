#!/usr/bin/env python3
"""
vLLM Client Integration
Handles communication with vLLM server for LLM inference
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import requests
from openai import OpenAI


@dataclass
class InferenceRequest:
    """Represents a single inference request"""
    node_id: str
    prompt: str
    agent_name: str
    node_type: str
    max_tokens: int = 512
    temperature: float = 0.7
    tools: Optional[List[Dict]] = None


@dataclass
class InferenceResponse:
    """Represents an inference response"""
    node_id: str
    content: str
    finish_reason: str
    tokens_used: int
    latency_ms: float
    tool_calls: Optional[List[Dict]] = None


class VLLMClient:
    """Client for interacting with vLLM server"""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000/v1",
        api_key: str = "sk-local-demo",
        model_name: str = "meta-llama/Llama-3.1-8B-Instruct",
        timeout: int = 120
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout

        # Initialize OpenAI client pointing to vLLM
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout
        )

        self.total_requests = 0
        self.total_tokens = 0
        self.total_latency = 0.0

    def check_health(self) -> bool:
        """Check if vLLM server is healthy"""
        try:
            response = requests.get(
                f"{self.base_url.replace('/v1', '')}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False

    def get_models(self) -> List[str]:
        """Get list of available models"""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return [model['id'] for model in data.get('data', [])]
            return []
        except Exception as e:
            print(f"Failed to get models: {e}")
            return []

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        """
        Generate response for a single request
        """
        start_time = time.time()

        try:
            messages = [{"role": "user", "content": request.prompt}]

            # Prepare API call parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            }

            # Add tools if specified
            if request.tools:
                params["tools"] = request.tools
                params["tool_choice"] = "auto"

            # Call vLLM via OpenAI-compatible API
            completion = self.client.chat.completions.create(**params)

            # Extract response
            message = completion.choices[0].message
            content = message.content or ""
            finish_reason = completion.choices[0].finish_reason
            tokens_used = completion.usage.total_tokens

            # Extract tool calls if present
            tool_calls = None
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    }
                    for tc in message.tool_calls
                ]

            latency_ms = (time.time() - start_time) * 1000

            # Update stats
            self.total_requests += 1
            self.total_tokens += tokens_used
            self.total_latency += latency_ms

            return InferenceResponse(
                node_id=request.node_id,
                content=content,
                finish_reason=finish_reason,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                tool_calls=tool_calls
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            print(f"Error generating response for {request.node_id}: {e}")

            return InferenceResponse(
                node_id=request.node_id,
                content=f"ERROR: {str(e)}",
                finish_reason="error",
                tokens_used=0,
                latency_ms=latency_ms,
                tool_calls=None
            )

    def batch_generate(
        self,
        requests: List[InferenceRequest],
        max_parallel: int = 4
    ) -> List[InferenceResponse]:
        """
        Generate responses for multiple requests
        Note: vLLM handles batching internally via continuous batching
        We send requests sequentially but vLLM will batch them
        """
        responses = []

        # For now, process sequentially - vLLM batches internally
        # TODO: Use async/concurrent requests for true parallelism
        for req in requests:
            response = self.generate(req)
            responses.append(response)

        return responses

    def get_statistics(self) -> Dict[str, Any]:
        """Get client statistics"""
        avg_latency = self.total_latency / self.total_requests if self.total_requests > 0 else 0

        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency,
            "average_latency_ms": avg_latency,
            "average_tokens_per_request": self.total_tokens / self.total_requests if self.total_requests > 0 else 0
        }


class ToolRegistry:
    """Registry for tool/function definitions for agent tool calls"""

    @staticmethod
    def get_spotify_tools() -> List[Dict]:
        """Get Spotify API tool definitions"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "show_liked_songs",
                    "description": "Get a list of songs you have liked on Spotify",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "access_token": {
                                "type": "string",
                                "description": "Access token obtained from spotify app login"
                            },
                            "page_index": {
                                "type": "integer",
                                "description": "The index of the page to return",
                                "default": 0
                            },
                            "page_limit": {
                                "type": "integer",
                                "description": "The maximum number of results to return per page",
                                "default": 5
                            }
                        },
                        "required": ["access_token"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "follow_artist",
                    "description": "Follow an artist on Spotify",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "access_token": {
                                "type": "string",
                                "description": "Access token for Spotify"
                            },
                            "artist_id": {
                                "type": "integer",
                                "description": "ID of the artist to follow"
                            }
                        },
                        "required": ["access_token", "artist_id"]
                    }
                }
            }
        ]

    @staticmethod
    def get_supervisor_tools() -> List[Dict]:
        """Get Supervisor API tool definitions"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "show_account_passwords",
                    "description": "Show your supervisor's app account passwords",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "show_profile",
                    "description": "Show your supervisor's profile information",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_task",
                    "description": "Mark the currently active task as complete",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["success", "fail"],
                                "description": "Status of task completion"
                            }
                        },
                        "required": ["status"]
                    }
                }
            }
        ]

    @staticmethod
    def get_tools_for_agent(agent_name: str) -> List[Dict]:
        """Get tool definitions for a specific agent"""
        agent_name_lower = agent_name.lower()
        if "spotify" in agent_name_lower:
            return ToolRegistry.get_spotify_tools()
        elif "supervisor" in agent_name_lower:
            return ToolRegistry.get_supervisor_tools()
        else:
            return []


if __name__ == "__main__":
    # Test the client
    client = VLLMClient()

    # Check health
    print("Checking vLLM server health...")
    if client.check_health():
        print("✓ Server is healthy")
    else:
        print("✗ Server is not responding")
        exit(1)

    # Get models
    print("\nAvailable models:")
    models = client.get_models()
    for model in models:
        print(f"  - {model}")

    # Test inference
    print("\nTesting inference...")
    request = InferenceRequest(
        node_id="test_node",
        prompt="You are a helpful assistant. Say hello!",
        agent_name="test_agent",
        node_type="test",
        max_tokens=50
    )

    response = client.generate(request)
    print(f"Response: {response.content}")
    print(f"Latency: {response.latency_ms:.2f}ms")
    print(f"Tokens: {response.tokens_used}")

    # Print statistics
    print("\nClient Statistics:")
    stats = client.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
