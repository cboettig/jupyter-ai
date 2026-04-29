"""Registry mapping harness id to adapter."""
from __future__ import annotations

from typing import Iterable

from .adapter import HarnessAdapter


class HarnessNotFoundError(KeyError):
    pass


class HarnessRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, HarnessAdapter] = {}

    def register(self, adapter: HarnessAdapter) -> None:
        if adapter.id in self._adapters:
            raise ValueError(f"Harness {adapter.id!r} already registered")
        self._adapters[adapter.id] = adapter

    def get(self, harness_id: str) -> HarnessAdapter:
        try:
            return self._adapters[harness_id]
        except KeyError as exc:
            raise HarnessNotFoundError(harness_id) from exc

    def list(self) -> Iterable[HarnessAdapter]:
        return list(self._adapters.values())
