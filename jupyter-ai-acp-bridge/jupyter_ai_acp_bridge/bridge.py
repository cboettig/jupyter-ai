"""ChatBridge: per-chat harness binding state."""
from __future__ import annotations

from typing import Any, Optional

from .adapter import HarnessAdapter

METADATA_KEY = "acp_bridge"


class AlreadyBoundError(RuntimeError):
    pass


class NotBoundError(RuntimeError):
    pass


class ChatBridge:
    def __init__(
        self,
        chat_id: str,
        ychat: Optional[Any] = None,
        registry: Optional[Any] = None,
    ) -> None:
        self.chat_id = chat_id
        self.ychat = ychat
        self._adapter: Optional[HarnessAdapter] = None
        self._persona: Optional[Any] = None
        if ychat is not None and registry is not None:
            existing = ychat.get_metadata().get(METADATA_KEY)
            if existing and "harness_id" in existing:
                self._adapter = registry.get(existing["harness_id"])

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

    def bind(self, adapter: HarnessAdapter, *, parent: Any = None) -> None:
        if self._adapter is not None:
            raise AlreadyBoundError(
                f"chat {self.chat_id} already bound to {self._adapter.id}"
            )
        self._adapter = adapter
        self._persona = None
        if adapter.persona_class is not None:
            self._persona = adapter.persona_class(
                parent=parent,
                ychat=self.ychat,
                executable=adapter.executable_factory(),
            )
        if self.ychat is not None:
            self.ychat.set_metadata(METADATA_KEY, {"harness_id": adapter.id})

    @property
    def persona(self) -> Any:
        return self._persona
