"""
LLM Providers - Predefined configurations for mainstream LLM services

Supports both international and domestic (Chinese) providers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class ProviderRegion(Enum):
    """Provider region"""
    INTERNATIONAL = "international"
    CHINA = "china"


class ProviderType(Enum):
    """Provider API type"""
    OPENAI_COMPATIBLE = "openai"      # OpenAI-compatible API
    ANTHROPIC = "anthropic"            # Anthropic Claude API
    GOOGLE = "google"                  # Google Gemini API
    CUSTOM = "custom"                  # Custom API


@dataclass
class ModelInfo:
    """Model information"""
    id: str
    name: str
    max_tokens: int
    supports_tools: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True
    description: str = ""


@dataclass
class ProviderInfo:
    """LLM Provider information"""
    id: str
    name: str
    region: ProviderRegion
    type: ProviderType
    base_url: str
    api_key_env: str
    models: List[ModelInfo] = field(default_factory=list)
    default_model: str = ""
    embedding_models: List[ModelInfo] = field(default_factory=list)
    default_embedding_model: str = ""
    website: str = ""
    docs: str = ""


# ============================================================
# International Providers
# ============================================================

OPENAI_PROVIDER = ProviderInfo(
    id="openai",
    name="OpenAI",
    region=ProviderRegion.INTERNATIONAL,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="https://api.openai.com/v1",
    api_key_env="OPENAI_API_KEY",
    models=[
        ModelInfo("gpt-4o", "GPT-4o", 128000, True, True, True, "Most advanced multimodal model"),
        ModelInfo("gpt-4o-mini", "GPT-4o Mini", 128000, True, True, True, "Fast and affordable"),
        ModelInfo("gpt-4-turbo", "GPT-4 Turbo", 128000, True, True, True, "Previous flagship"),
        ModelInfo("gpt-4", "GPT-4", 8192, True, False, True, "Classic GPT-4"),
        ModelInfo("gpt-3.5-turbo", "GPT-3.5 Turbo", 16384, True, False, True, "Fast and cheap"),
        ModelInfo("o1", "o1", 200000, False, False, False, "Advanced reasoning"),
        ModelInfo("o1-mini", "o1 Mini", 128000, False, False, False, "Fast reasoning"),
    ],
    default_model="gpt-4o-mini",
    embedding_models=[
        ModelInfo("text-embedding-3-large", "Text Embedding 3 Large", 8191),
        ModelInfo("text-embedding-3-small", "Text Embedding 3 Small", 8191),
        ModelInfo("text-embedding-ada-002", "Ada 002", 8191),
    ],
    default_embedding_model="text-embedding-3-small",
    website="https://openai.com",
    docs="https://platform.openai.com/docs"
)

ANTHROPIC_PROVIDER = ProviderInfo(
    id="anthropic",
    name="Anthropic (Claude)",
    region=ProviderRegion.INTERNATIONAL,
    type=ProviderType.ANTHROPIC,
    base_url="https://api.anthropic.com/v1",
    api_key_env="ANTHROPIC_API_KEY",
    models=[
        ModelInfo("claude-sonnet-4-20250514", "Claude Sonnet 4", 200000, True, True, True, "Latest Claude, best balance"),
        ModelInfo("claude-opus-4-20250514", "Claude Opus 4", 200000, True, True, True, "Most capable Claude"),
        ModelInfo("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", 200000, True, True, True, "Fast and intelligent"),
        ModelInfo("claude-3-5-haiku-20241022", "Claude 3.5 Haiku", 200000, True, False, True, "Fastest Claude"),
        ModelInfo("claude-3-opus-20240229", "Claude 3 Opus", 200000, True, True, True, "Previous flagship"),
    ],
    default_model="claude-sonnet-4-20250514",
    embedding_models=[],
    default_embedding_model="",
    website="https://anthropic.com",
    docs="https://docs.anthropic.com"
)

GOOGLE_PROVIDER = ProviderInfo(
    id="google",
    name="Google AI (Gemini)",
    region=ProviderRegion.INTERNATIONAL,
    type=ProviderType.GOOGLE,
    base_url="https://generativelanguage.googleapis.com/v1beta",
    api_key_env="GOOGLE_API_KEY",
    models=[
        ModelInfo("gemini-2.0-flash", "Gemini 2.0 Flash", 1000000, True, True, True, "Fast multimodal"),
        ModelInfo("gemini-1.5-pro", "Gemini 1.5 Pro", 2000000, True, True, True, "Long context"),
        ModelInfo("gemini-1.5-flash", "Gemini 1.5 Flash", 1000000, True, True, True, "Fast and efficient"),
        ModelInfo("gemini-1.0-pro", "Gemini 1.0 Pro", 32000, True, False, True, "Standard model"),
    ],
    default_model="gemini-2.0-flash",
    embedding_models=[
        ModelInfo("text-embedding-004", "Text Embedding 004", 8192),
    ],
    default_embedding_model="text-embedding-004",
    website="https://ai.google.dev",
    docs="https://ai.google.dev/docs"
)

AZURE_OPENAI_PROVIDER = ProviderInfo(
    id="azure",
    name="Azure OpenAI",
    region=ProviderRegion.INTERNATIONAL,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="",  # User must provide
    api_key_env="AZURE_OPENAI_API_KEY",
    models=[
        ModelInfo("gpt-4o", "GPT-4o", 128000, True, True, True),
        ModelInfo("gpt-4", "GPT-4", 8192, True, False, True),
        ModelInfo("gpt-35-turbo", "GPT-3.5 Turbo", 16384, True, False, True),
    ],
    default_model="gpt-4o",
    website="https://azure.microsoft.com/en-us/products/ai-services/openai-service",
    docs="https://learn.microsoft.com/en-us/azure/ai-services/openai/"
)

# ============================================================
# Chinese (Domestic) Providers
# ============================================================

ALIYUN_PROVIDER = ProviderInfo(
    id="aliyun",
    name="阿里云通义千问 (Qwen)",
    region=ProviderRegion.CHINA,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key_env="ALIYUN_API_KEY",
    models=[
        ModelInfo("qwen-max", "通义千问 Max", 32000, True, True, True, "最强能力"),
        ModelInfo("qwen-plus", "通义千问 Plus", 128000, True, True, True, "超长上下文"),
        ModelInfo("qwen-turbo", "通义千问 Turbo", 128000, True, False, True, "快速响应"),
        ModelInfo("qwen-long", "通义千问 Long", 10000000, False, False, True, "千万级上下文"),
        ModelInfo("qwen-vl-max", "通义千问 VL Max", 32000, True, True, True, "视觉理解"),
        ModelInfo("qwen2.5-72b-instruct", "Qwen2.5 72B", 131072, True, False, True, "开源旗舰"),
        ModelInfo("qwen2.5-32b-instruct", "Qwen2.5 32B", 131072, True, False, True, "开源大模型"),
        ModelInfo("qwen2.5-14b-instruct", "Qwen2.5 14B", 131072, True, False, True, "开源中杯"),
        ModelInfo("qwen2.5-7b-instruct", "Qwen2.5 7B", 131072, True, False, True, "开源小杯"),
    ],
    default_model="qwen-plus",
    embedding_models=[
        ModelInfo("text-embedding-v3", "Text Embedding v3", 8192),
        ModelInfo("text-embedding-v2", "Text Embedding v2", 8192),
    ],
    default_embedding_model="text-embedding-v3",
    website="https://tongyi.aliyun.com",
    docs="https://help.aliyun.com/zh/dashscope/"
)

BAIDU_PROVIDER = ProviderInfo(
    id="baidu",
    name="百度文心一言 (ERNIE)",
    region=ProviderRegion.CHINA,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
    api_key_env="BAIDU_API_KEY",
    models=[
        ModelInfo("ernie-4.0-8k", "ERNIE 4.0", 8192, True, False, True, "旗舰模型"),
        ModelInfo("ernie-4.0-turbo-8k", "ERNIE 4.0 Turbo", 8192, True, False, True, "快速版"),
        ModelInfo("ernie-3.5-8k", "ERNIE 3.5", 8192, True, False, True, "均衡模型"),
        ModelInfo("ernie-speed-8k", "ERNIE Speed", 8192, True, False, True, "极速模型"),
        ModelInfo("ernie-lite-8k", "ERNIE Lite", 8192, True, False, True, "轻量模型"),
    ],
    default_model="ernie-4.0-8k",
    embedding_models=[
        ModelInfo("Embedding-V1", "Embedding V1", 2048),
    ],
    default_embedding_model="Embedding-V1",
    website="https://yiyan.baidu.com",
    docs="https://cloud.baidu.com/doc/WENXINWORKSHOP/index.html"
)

ZHIPU_PROVIDER = ProviderInfo(
    id="zhipu",
    name="智谱AI (GLM)",
    region=ProviderRegion.CHINA,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key_env="ZHIPU_API_KEY",
    models=[
        ModelInfo("glm-4-plus", "GLM-4 Plus", 128000, True, True, True, "最新旗舰"),
        ModelInfo("glm-4-0520", "GLM-4", 128000, True, False, True, "主力模型"),
        ModelInfo("glm-4-air", "GLM-4 Air", 128000, True, False, True, "高速模型"),
        ModelInfo("glm-4-flash", "GLM-4 Flash", 128000, True, False, True, "免费快速"),
        ModelInfo("glm-4v-plus", "GLM-4V Plus", 8192, True, True, True, "视觉理解"),
        ModelInfo("glm-4-long", "GLM-4 Long", 1000000, False, False, True, "长文本"),
    ],
    default_model="glm-4-flash",
    embedding_models=[
        ModelInfo("embedding-3", "Embedding 3", 8192),
    ],
    default_embedding_model="embedding-3",
    website="https://bigmodel.cn",
    docs="https://open.bigmodel.cn/dev/api"
)

MOONSHOT_PROVIDER = ProviderInfo(
    id="moonshot",
    name="月之暗面 (Kimi)",
    region=ProviderRegion.CHINA,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="https://api.moonshot.cn/v1",
    api_key_env="MOONSHOT_API_KEY",
    models=[
        ModelInfo("moonshot-v1-8k", "Moonshot V1 8K", 8192, True, False, True, "标准模型"),
        ModelInfo("moonshot-v1-32k", "Moonshot V1 32K", 32768, True, False, True, "长文本"),
        ModelInfo("moonshot-v1-128k", "Moonshot V1 128K", 131072, True, False, True, "超长文本"),
    ],
    default_model="moonshot-v1-8k",
    embedding_models=[],
    website="https://kimi.moonshot.cn",
    docs="https://platform.moonshot.cn/docs"
)

XFYUN_PROVIDER = ProviderInfo(
    id="xfyun",
    name="讯飞星火 (Spark)",
    region=ProviderRegion.CHINA,
    type=ProviderType.CUSTOM,
    base_url="https://spark-api-open.xf-yun.com/v1",
    api_key_env="XFYUN_API_KEY",
    models=[
        ModelInfo("generalv3.5", "星火 V3.5", 8192, True, False, True, "最新版本"),
        ModelInfo("generalv3", "星火 V3.0", 8192, True, False, True, "稳定版本"),
        ModelInfo("generalv2", "星火 V2.0", 8192, False, False, True, "经典版本"),
        ModelInfo("4.0Ultra", "星火 Ultra", 8192, True, False, True, "旗舰版本"),
    ],
    default_model="generalv3.5",
    embedding_models=[
        ModelInfo("embeddings", "星火 Embedding", 1024),
    ],
    website="https://xinghuo.xfyun.cn",
    docs="https://www.xfyun.cn/doc/spark"
)

BAICHUAN_PROVIDER = ProviderInfo(
    id="baichuan",
    name="百川智能 (Baichuan)",
    region=ProviderRegion.CHINA,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="https://api.baichuan-ai.com/v1",
    api_key_env="BAICHUAN_API_KEY",
    models=[
        ModelInfo("Baichuan4", "Baichuan 4", 128000, True, True, True, "最新旗舰"),
        ModelInfo("Baichuan3-Turbo", "Baichuan 3 Turbo", 32000, True, False, True, "快速版"),
        ModelInfo("Baichuan3-Turbo-128k", "Baichuan 3 Turbo 128K", 131072, True, False, True, "长文本"),
        ModelInfo("Baichuan2-Turbo", "Baichuan 2 Turbo", 32000, True, False, True, "经典版"),
    ],
    default_model="Baichuan4",
    embedding_models=[],
    website="https://www.baichuan-ai.com",
    docs="https://platform.baichuan-ai.com/docs"
)

MINIMAX_PROVIDER = ProviderInfo(
    id="minimax",
    name="MiniMax",
    region=ProviderRegion.CHINA,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="https://api.minimax.chat/v1",
    api_key_env="MINIMAX_API_KEY",
    models=[
        ModelInfo("abab6.5s-chat", "abab 6.5s", 245000, True, False, True, "极速旗舰"),
        ModelInfo("abab6.5g-chat", "abab 6.5g", 245000, True, False, True, "均衡旗舰"),
        ModelInfo("abab6.5-chat", "abab 6.5", 8192, True, False, True, "标准旗舰"),
        ModelInfo("abab5.5-chat", "abab 5.5", 16384, True, False, True, "经典版本"),
    ],
    default_model="abab6.5s-chat",
    embedding_models=[
        ModelInfo("embo-01", "Embo 01", 2048),
    ],
    default_embedding_model="embo-01",
    website="https://www.minimaxi.com",
    docs="https://www.minimaxi.com/document"
)

DEEPSEEK_PROVIDER = ProviderInfo(
    id="deepseek",
    name="DeepSeek (深度求索)",
    region=ProviderRegion.CHINA,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="https://api.deepseek.com/v1",
    api_key_env="DEEPSEEK_API_KEY",
    models=[
        ModelInfo("deepseek-chat", "DeepSeek Chat", 64000, True, False, True, "对话模型"),
        ModelInfo("deepseek-reasoner", "DeepSeek Reasoner", 64000, False, False, True, "推理模型 (R1)"),
        ModelInfo("deepseek-coder", "DeepSeek Coder", 16384, True, False, True, "代码模型"),
    ],
    default_model="deepseek-chat",
    embedding_models=[],
    website="https://www.deepseek.com",
    docs="https://platform.deepseek.com/docs"
)

SILICONFLOW_PROVIDER = ProviderInfo(
    id="siliconflow",
    name="SiliconFlow (硅基流动)",
    region=ProviderRegion.CHINA,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="https://api.siliconflow.cn/v1",
    api_key_env="SILICONFLOW_API_KEY",
    models=[
        ModelInfo("Qwen/Qwen2.5-72B-Instruct", "Qwen2.5 72B", 32768, True, False, True),
        ModelInfo("Qwen/Qwen2.5-32B-Instruct", "Qwen2.5 32B", 32768, True, False, True),
        ModelInfo("deepseek-ai/DeepSeek-V3", "DeepSeek V3", 64000, True, False, True),
        ModelInfo("meta-llama/Llama-3.1-70B-Instruct", "Llama 3.1 70B", 131072, True, False, True),
        ModelInfo("THUDM/glm-4-9b-chat", "GLM-4 9B", 131072, True, False, True),
    ],
    default_model="Qwen/Qwen2.5-72B-Instruct",
    embedding_models=[
        ModelInfo("BAAI/bge-large-zh-v1.5", "BGE Large ZH", 512),
        ModelInfo("jinaai/jina-embeddings-v2-base-zh", "Jina ZH", 8192),
    ],
    default_embedding_model="BAAI/bge-large-zh-v1.5",
    website="https://siliconflow.cn",
    docs="https://docs.siliconflow.cn"
)

# ============================================================
# Local Providers
# ============================================================

OLLAMA_PROVIDER = ProviderInfo(
    id="ollama",
    name="Ollama (本地)",
    region=ProviderRegion.INTERNATIONAL,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="http://localhost:11434",
    api_key_env="",
    models=[
        ModelInfo("qwen2.5:latest", "Qwen2.5", 32768, True, False, True, "通义千问"),
        ModelInfo("llama3.2:latest", "Llama 3.2", 32768, True, False, True, "Meta Llama"),
        ModelInfo("deepseek-r1:latest", "DeepSeek R1", 64000, False, False, True, "深度推理"),
        ModelInfo("codellama:latest", "Code Llama", 16384, False, False, True, "代码生成"),
        ModelInfo("mistral:latest", "Mistral", 32768, True, False, True, "Mistral AI"),
        ModelInfo("gemma2:latest", "Gemma 2", 8192, True, False, True, "Google Gemma"),
        ModelInfo("phi4:latest", "Phi-4", 16384, True, False, True, "Microsoft Phi"),
        ModelInfo("yi:latest", "Yi", 32768, True, False, True, "零一万物"),
        ModelInfo("glm4:latest", "GLM-4", 131072, True, False, True, "智谱GLM"),
    ],
    default_model="qwen2.5:latest",
    embedding_models=[
        ModelInfo("nomic-embed-text:latest", "Nomic Embed Text", 8192),
        ModelInfo("mxbai-embed-large:latest", "MxBai Embed Large", 512),
    ],
    default_embedding_model="nomic-embed-text:latest",
    website="https://ollama.ai",
    docs="https://github.com/ollama/ollama"
)

VLLM_PROVIDER = ProviderInfo(
    id="vllm",
    name="vLLM (本地)",
    region=ProviderRegion.INTERNATIONAL,
    type=ProviderType.OPENAI_COMPATIBLE,
    base_url="http://localhost:8000/v1",
    api_key_env="",
    models=[],  # User must configure
    default_model="",
    website="https://github.com/vllm-project/vllm",
    docs="https://vllm.readthedocs.io"
)

# ============================================================
# Provider Registry
# ============================================================

PROVIDERS: Dict[str, ProviderInfo] = {
    # International
    "openai": OPENAI_PROVIDER,
    "anthropic": ANTHROPIC_PROVIDER,
    "google": GOOGLE_PROVIDER,
    "azure": AZURE_OPENAI_PROVIDER,
    # Chinese
    "aliyun": ALIYUN_PROVIDER,
    "baidu": BAIDU_PROVIDER,
    "zhipu": ZHIPU_PROVIDER,
    "moonshot": MOONSHOT_PROVIDER,
    "xfyun": XFYUN_PROVIDER,
    "baichuan": BAICHUAN_PROVIDER,
    "minimax": MINIMAX_PROVIDER,
    "deepseek": DEEPSEEK_PROVIDER,
    "siliconflow": SILICONFLOW_PROVIDER,
    # Local
    "ollama": OLLAMA_PROVIDER,
    "vllm": VLLM_PROVIDER,
}


def get_provider(provider_id: str) -> Optional[ProviderInfo]:
    """Get provider by ID"""
    return PROVIDERS.get(provider_id)


def get_providers_by_region(region: ProviderRegion) -> List[ProviderInfo]:
    """Get providers by region"""
    return [p for p in PROVIDERS.values() if p.region == region]


def list_providers() -> List[str]:
    """List all provider IDs"""
    return list(PROVIDERS.keys())


def get_chinese_providers() -> List[ProviderInfo]:
    """Get all Chinese providers"""
    return get_providers_by_region(ProviderRegion.CHINA)


def get_international_providers() -> List[ProviderInfo]:
    """Get all international providers"""
    return get_providers_by_region(ProviderRegion.INTERNATIONAL)


def get_local_providers() -> List[ProviderInfo]:
    """Get all local (self-hosted) providers"""
    return [PROVIDERS["ollama"], PROVIDERS["vllm"]]
