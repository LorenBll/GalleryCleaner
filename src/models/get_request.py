from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class GetRequest:
    url: str
    timeout: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)
