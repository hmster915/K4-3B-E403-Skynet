"""Common tool result contract."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ToolResult:
    content: str
    source: str | None = None


class Tool(Protocol):
    def run(self, query: str) -> ToolResult: ...
