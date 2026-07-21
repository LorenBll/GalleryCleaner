from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PostResponse:
    status_code: int
    reason: str
    body: str
    body_size: int
    headers: dict[str, str]
    json_body: dict | list | str | int | float | bool | None = None
