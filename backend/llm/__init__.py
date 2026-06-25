from .base import LLMClient
from .deepseek import DeepSeekClient
from .openai import OpenAIClient
from backend.config import get_settings

def get_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.llm_provider == "deepseek":
        return DeepSeekClient(api_key=settings.llm_api_key, model=settings.llm_model, base_url=settings.llm_base_url)
    elif settings.llm_provider == "openai":
        return OpenAIClient(api_key=settings.llm_api_key, model=settings.llm_model, base_url=settings.llm_base_url)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
