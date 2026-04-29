"""BridgeManager: process-wide map of chat_id -> ChatBridge."""
from __future__ import annotations

from typing import Optional

from .bridge import ChatBridge


class BridgeManager:
    def __init__(self) -> None:
        self._bridges: dict[str, ChatBridge] = {}

    def get_or_create(self, chat_id: str) -> ChatBridge:
        if chat_id not in self._bridges:
            self._bridges[chat_id] = ChatBridge(chat_id=chat_id)
        return self._bridges[chat_id]

    def lookup(self, chat_id: str) -> Optional[ChatBridge]:
        return self._bridges.get(chat_id)

    def remove(self, chat_id: str) -> None:
        self._bridges.pop(chat_id, None)
