from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], stream: bool = False) -> str:
        pass

    @abstractmethod
    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        pass
