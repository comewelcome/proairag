from abc import ABC, abstractmethod
from src.config import get_settings


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini", base_url: str = "", max_tokens: int = 500):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"
        self.max_tokens = max_tokens

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        import httpx
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
                timeout=300,
            )
            response.raise_for_status()
            data = response.json()
            # Handle reasoning models that return content in reasoning_content
            message = data["choices"][0]["message"]
            return message.get("content") or message.get("reasoning_content") or ""


class LocalProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1", max_tokens: int = 500):
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        import httpx
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "max_tokens": self.max_tokens,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=body,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            return message.get("content") or message.get("reasoning_content") or ""


class FallbackProvider(LLMProvider):
    """Returns context-only response when no LLM is available."""

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        return prompt


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider
    if provider == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_api_base,
            max_tokens=settings.llm_max_tokens,
        )
    elif provider == "ollama":
        return LocalProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            max_tokens=settings.llm_max_tokens,
        )
    else:
        return FallbackProvider()
