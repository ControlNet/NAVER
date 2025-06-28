from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..context.context import Context

class BaseLogicModel(ABC):

    @abstractmethod
    async def generate(self, context: Context, query: str, interested_entities: list[str], 
                       overwrite_feedback: str | None = None, previous_response: str | None = None) -> tuple[str, str]:
        ...

    @abstractmethod
    def execute(self, code: str) -> Any:
        ...
