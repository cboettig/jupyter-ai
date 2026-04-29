"""ChatBridge: per-chat harness binding state."""
from __future__ import annotations

from typing import Optional

from .adapter import HarnessAdapter


class AlreadyBoundError(RuntimeError):
    pass


class NotBoundError(RuntimeError):
    pass


class ChatBridge:
    def __init__(self, chat_id: str) -> None:
        self.chat_id = chat_id
        self._adapter: Optional[HarnessAdapter] = None

    @property
    def is_draft(self) -> bool:
        return self._adapter is None

    @property
    def is_bound(self) -> bool:
        return self._adapter is not None

    @property
    def harness_id(self) -> Optional[str]:
        return self._adapter.id if self._adapter else None

    @property
    def adapter(self) -> HarnessAdapter:
        if self._adapter is None:
            raise NotBoundError(f"chat {self.chat_id} has no harness bound")
        return self._adapter

    def bind(self, adapter: HarnessAdapter) -> None:
        if self._adapter is not None:
            raise AlreadyBoundError(
                f"chat {self.chat_id} already bound to {self._adapter.id}"
            )
        self._adapter = adapter
