"""
LLM Client - Unified interface for language models

Supports multiple backends:
- International: OpenAI, Anthropic (Claude), Google (Gemini), Azure
- Chinese: 通义千问, 文心一言, 智谱GLM, DeepSeek, Kimi, etc.
- Local: Ollama, vLLM
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncIterator, Callable
import aiohttp
import json
import os

from ada.core.llm_providers import (
    ProviderInfo, ProviderType, ProviderRegion,
    get_provider, PROVIDERS
)


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

    def to_anthropic(self) -> Dict[str, Any]:
        """Convert to Anthropic format"""
        return {"role": self.role, "content": self.content}


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

    def to_anthropic_format(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters
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

    @classmethod
    def from_anthropic(cls, data: Dict) -> "ToolCall":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            arguments=data.get("input", {})
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
        model: str = "qwen2.5:latest",
        base_url: str = "http://localhost:11434"
    ):
        self.model = model
        self.base_url = base_url
        self._embedding_model = "nomic-embed-text:latest"

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
        async with aiohttp.ClientSession() as session:
            embeddings = []
            for text in texts:
                async with session.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self._embedding_model, "prompt": text}
                ) as resp:
                    result = await resp.json()
                    embeddings.append(result.get("embedding", []))
            return embeddings

    def set_embedding_model(self, model: str):
        """Set the embedding model"""
        self._embedding_model = model


class OpenAICompatibleBackend(LLMBackend):
    """
    OpenAI-compatible backend

    Supports: OpenAI, DeepSeek, 通义千问, 智谱GLM, Kimi, etc.
    All providers that implement OpenAI API format.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        provider_name: str = "OpenAI"
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.provider_name = provider_name
        self._embedding_model = "text-embedding-3-small"

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
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"{self.provider_name} API error: {error}")

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
                    "model": self._embedding_model,
                    "input": texts
                }
            ) as resp:
                result = await resp.json()
                return [d["embedding"] for d in result["data"]]

    def set_embedding_model(self, model: str):
        """Set the embedding model"""
        self._embedding_model = model


class AnthropicBackend(LLMBackend):
    """Anthropic Claude backend"""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str = None
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = "https://api.anthropic.com/v1"
        self._embedding_model = None

    async def generate(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response from Claude"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        # Separate system message
        system_prompt = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            else:
                chat_messages.append(m.to_anthropic())

        payload = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": chat_messages,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if tools:
            payload["tools"] = [t.to_anthropic_format() for t in tools]

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"Anthropic API error: {error}")

                result = await resp.json()

                # Extract content
                content = ""
                tool_calls = []
                for block in result.get("content", []):
                    if block.get("type") == "text":
                        content += block.get("text", "")
                    elif block.get("type") == "tool_use":
                        tool_calls.append(ToolCall.from_anthropic(block))

                return LLMResponse(
                    content=content,
                    tool_calls=tool_calls,
                    usage={
                        "prompt_tokens": result.get("usage", {}).get("input_tokens", 0),
                        "completion_tokens": result.get("usage", {}).get("output_tokens", 0)
                    },
                    model=self.model,
                    finish_reason=result.get("stop_reason", "")
                )

    async def stream(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens from Claude"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        # Separate system message
        system_prompt = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            else:
                chat_messages.append(m.to_anthropic())

        payload = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": chat_messages,
            "stream": True
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            ) as resp:
                async for line in resp.content:
                    if line and line.startswith(b"data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except json.JSONDecodeError:
                            continue

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Anthropic doesn't have embeddings API, use fallback"""
        raise NotImplementedError("Anthropic doesn't provide embeddings API. Use a different provider for embeddings.")


class GoogleBackend(LLMBackend):
    """Google Gemini backend"""

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: str = None
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._embedding_model = "text-embedding-004"

    async def generate(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response from Gemini"""
        # Convert messages to Gemini format
        contents = []
        system_instruction = None

        for m in messages:
            if m.role == "system":
                system_instruction = {"parts": [{"text": m.content}]}
            else:
                role = "user" if m.role == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": m.content}]
                })

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": kwargs.get("max_tokens", 8192),
                "temperature": kwargs.get("temperature", 0.7),
            }
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"Google API error: {error}")

                result = await resp.json()

                # Extract content
                content = ""
                for candidate in result.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        content += part.get("text", "")

                return LLMResponse(
                    content=content,
                    usage={
                        "prompt_tokens": result.get("usageMetadata", {}).get("promptTokenCount", 0),
                        "completion_tokens": result.get("usageMetadata", {}).get("candidatesTokenCount", 0)
                    },
                    model=self.model,
                    finish_reason=result.get("candidates", [{}])[0].get("finishReason", "")
                )

    async def stream(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens from Gemini"""
        # Convert messages to Gemini format
        contents = []
        for m in messages:
            role = "user" if m.role == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m.content}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": kwargs.get("max_tokens", 8192),
                "temperature": kwargs.get("temperature", 0.7),
            }
        }

        url = f"{self.base_url}/models/{self.model}:streamGenerateContent?key={self.api_key}&alt=sse"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                async for line in resp.content:
                    if line and line.startswith(b"data: "):
                        try:
                            data = json.loads(line[6:])
                            for candidate in data.get("candidates", []):
                                for part in candidate.get("content", {}).get("parts", []):
                                    text = part.get("text", "")
                                    if text:
                                        yield text
                        except json.JSONDecodeError:
                            continue

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Gemini"""
        embeddings = []

        async with aiohttp.ClientSession() as session:
            for text in texts:
                url = f"{self.base_url}/models/{self._embedding_model}:embedContent?key={self.api_key}"
                payload = {
                    "model": f"models/{self._embedding_model}",
                    "content": {"parts": [{"text": text}]}
                }

                async with session.post(url, json=payload) as resp:
                    result = await resp.json()
                    embeddings.append(result.get("embedding", {}).get("values", []))

        return embeddings

    def set_embedding_model(self, model: str):
        """Set the embedding model"""
        self._embedding_model = model


class LLMClient:
    """
    Unified LLM client interface.

    Example:
        # From provider config
        client = LLMClient.from_provider("openai", model="gpt-4o")

        # Or from custom config
        client = LLMClient.from_config({
            "type": "openai",
            "model": "gpt-4o",
            "api_key": "sk-..."
        })

        # Local Ollama
        client = LLMClient.from_provider("ollama", model="qwen2.5:latest")

        # Generate
        response = await client.generate("Hello, how are you?")

        # With tools
        response = await client.generate(
            "What's the weather?",
            tools=[weather_tool]
        )
    """

    def __init__(self, backend: LLMBackend, provider_id: str = "custom"):
        self._backend = backend
        self.provider_id = provider_id

    @classmethod
    def from_provider(
        cls,
        provider_id: str,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        **kwargs
    ) -> "LLMClient":
        """Create client from provider ID"""

        # Special handling for local providers
        if provider_id == "ollama":
            backend = OllamaBackend(
                model=model or "qwen2.5:latest",
                base_url=base_url or "http://localhost:11434"
            )
            if kwargs.get("embedding_model"):
                backend.set_embedding_model(kwargs["embedding_model"])
            return cls(backend, provider_id)

        if provider_id == "vllm":
            backend = OpenAICompatibleBackend(
                model=model or "",
                api_key=api_key or "dummy",
                base_url=base_url or "http://localhost:8000/v1",
                provider_name="vLLM"
            )
            return cls(backend, provider_id)

        # Get provider info
        provider = get_provider(provider_id)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_id}")

        # Get API key
        if not api_key:
            api_key = os.environ.get(provider.api_key_env, "")

        # Use defaults from provider
        if not model:
            model = provider.default_model
        if not base_url:
            base_url = provider.base_url

        # Create backend based on provider type
        if provider.type == ProviderType.ANTHROPIC:
            backend = AnthropicBackend(model=model, api_key=api_key)
        elif provider.type == ProviderType.GOOGLE:
            backend = GoogleBackend(model=model, api_key=api_key)
        else:  # OPENAI_COMPATIBLE or CUSTOM
            backend = OpenAICompatibleBackend(
                model=model,
                api_key=api_key,
                base_url=base_url,
                provider_name=provider.name
            )

        # Set embedding model if specified
        if kwargs.get("embedding_model"):
            if hasattr(backend, 'set_embedding_model'):
                backend.set_embedding_model(kwargs["embedding_model"])

        return cls(backend, provider_id)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "LLMClient":
        """Create client from configuration dict"""
        return cls.from_provider(
            provider_id=config.get("provider", config.get("type", "ollama")),
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            embedding_model=config.get("embedding_model"),
            **{k: v for k, v in config.items()
               if k not in ["provider", "type", "model", "api_key", "base_url", "embedding_model"]}
        )

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
