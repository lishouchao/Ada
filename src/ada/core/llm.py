"""
LLM Client - Unified interface for language models

Supports multiple backends:
- Cloud: OpenAI, Anthropic, Google, DeepSeek
- Local: Ollama, vLLM, llama.cpp
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncIterator, Callable
import aiohttp
import json


@dataclass
class Message:
    """Chat message"""
    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass
class ToolDefinition:
    """Tool/Function definition for LLM"""
    name: str
    description: str
    parameters: Dict[str, Any]

    def to_openai_format(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


@dataclass
class ToolCall:
    """Tool call from LLM"""
    id: str
    name: str
    arguments: Dict[str, Any]

    @classmethod
    def from_openai(cls, data: Dict) -> "ToolCall":
        return cls(
            id=data.get("id", ""),
            name=data.get("function", {}).get("name", ""),
            arguments=json.loads(data.get("function", {}).get("arguments", "{}"))
        )


@dataclass
class LLMResponse:
    """LLM response"""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = ""
    finish_reason: str = ""

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class LLMBackend(ABC):
    """Abstract base class for LLM backends"""

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens"""
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings"""
        pass


class OllamaBackend(LLMBackend):
    """Ollama backend for local models"""

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434"
    ):
        self.model = model
        self.base_url = base_url
        self._embedding_model = None

    async def generate(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response from Ollama"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "messages": [m.to_dict() for m in messages],
                "stream": False,
                **kwargs
            }

            if tools:
                payload["tools"] = [t.to_openai_format() for t in tools]

            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as resp:
                result = await resp.json()
                msg = result.get("message", {})

                tool_calls = []
                for tc in msg.get("tool_calls", []):
                    tool_calls.append(ToolCall(
                        id=tc.get("id", ""),
                        name=tc.get("function", {}).get("name", ""),
                        arguments=tc.get("function", {}).get("arguments", {})
                    ))

                return LLMResponse(
                    content=msg.get("content", ""),
                    tool_calls=tool_calls,
                    usage={
                        "prompt_tokens": result.get("prompt_eval_count", 0),
                        "completion_tokens": result.get("eval_count", 0)
                    },
                    model=self.model
                )

    async def stream(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "messages": [m.to_dict() for m in messages],
                "stream": True,
                **kwargs
            }

            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as resp:
                async for line in resp.content:
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                content = data["message"].get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Ollama"""
        model = self._embedding_model or "nomic-embed-text"

        async with aiohttp.ClientSession() as session:
            embeddings = []
            for text in texts:
                async with session.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": model, "prompt": text}
                ) as resp:
                    result = await resp.json()
                    embeddings.append(result.get("embedding", []))
            return embeddings

    def set_embedding_model(self, model: str):
        """Set the embedding model"""
        self._embedding_model = model


class OpenAICompatibleBackend(LLMBackend):
    """OpenAI-compatible backend (supports OpenAI, DeepSeek, vLLM, etc.)"""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1"
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    async def generate(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            **kwargs
        }

        if tools:
            payload["tools"] = [t.to_openai_format() for t in tools]

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as resp:
                result = await resp.json()
                choice = result["choices"][0]
                msg = choice["message"]

                tool_calls = []
                for tc in msg.get("tool_calls", []):
                    tool_calls.append(ToolCall.from_openai(tc))

                return LLMResponse(
                    content=msg.get("content", "") or "",
                    tool_calls=tool_calls,
                    usage=result.get("usage", {}),
                    model=self.model,
                    finish_reason=choice.get("finish_reason", "")
                )

    async def stream(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            **kwargs
        }

        if tools:
            payload["tools"] = [t.to_openai_format() for t in tools]

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as resp:
                async for line in resp.content:
                    if line and line.startswith(b"data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("choices"):
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except (json.JSONDecodeError, IndexError):
                            continue

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json={
                    "model": "text-embedding-3-small",
                    "input": texts
                }
            ) as resp:
                result = await resp.json()
                return [d["embedding"] for d in result["data"]]


class LLMClient:
    """
    Unified LLM client interface.

    Example:
        # From config
        client = LLMClient.from_config({
            "type": "ollama",
            "model": "qwen2.5:7b"
        })

        # Or directly
        client = LLMClient(OllamaBackend(model="qwen2.5:7b"))

        # Generate
        response = await client.generate("Hello, how are you?")

        # With tools
        response = await client.generate(
            "What's the weather?",
            tools=[weather_tool]
        )
    """

    def __init__(self, backend: LLMBackend):
        self._backend = backend

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "LLMClient":
        """Create client from configuration dict"""
        backend_type = config.get("type", "ollama")

        if backend_type == "ollama":
            backend = OllamaBackend(
                model=config.get("model", "qwen2.5:7b"),
                base_url=config.get("base_url", "http://localhost:11434")
            )
            if config.get("embedding_model"):
                backend.set_embedding_model(config["embedding_model"])

        elif backend_type in ["openai", "deepseek", "vllm"]:
            base_urls = {
                "openai": "https://api.openai.com/v1",
                "deepseek": "https://api.deepseek.com/v1",
            }
            backend = OpenAICompatibleBackend(
                model=config["model"],
                api_key=config["api_key"],
                base_url=config.get("base_url", base_urls.get(backend_type, ""))
            )

        else:
            raise ValueError(f"Unknown backend type: {backend_type}")

        return cls(backend)

    async def generate(
        self,
        prompt: str,
        system: str = None,
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response"""
        messages = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))

        return await self._backend.generate(messages, tools, **kwargs)

    async def chat(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> LLMResponse:
        """Continue a chat conversation"""
        return await self._backend.generate(messages, tools, **kwargs)

    async def stream(
        self,
        prompt: str,
        system: str = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens"""
        messages = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))

        async for chunk in self._backend.stream(messages, **kwargs):
            yield chunk

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        return await self._backend.embed(texts)

    async def embed_one(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embeddings = await self._backend.embed([text])
        return embeddings[0] if embeddings else []
