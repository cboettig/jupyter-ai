"""Bridge integration with jupyter-ai-router."""
from __future__ import annotations

import asyncio
from typing import Any

from .manager import BridgeManager
from .registry import HarnessNotFoundError, HarnessRegistry


class BridgeRouterIntegration:
    """Bridges between jupyter-ai-router observers and the per-chat ChatBridge.

    Created once per Jupyter Server. `attach(router)` registers the chat-init
    observer; that observer in turn registers a per-chat msg observer when each
    chat connects.
    """

    def __init__(
        self,
        *,
        registry: HarnessRegistry,
        bridge_manager: BridgeManager,
        persona_managers: dict[str, Any],
    ) -> None:
        self.registry = registry
        self.bridge_manager = bridge_manager
        self.persona_managers = persona_managers
        self.router: Any = None

    def attach(self, router: Any) -> None:
        self.router = router
        router.observe_chat_init(self._on_chat_init)

    def _on_chat_init(self, room_id: str, ychat: Any) -> None:
        bridge = self.bridge_manager.get_or_create(room_id)
        bridge.ychat = ychat
        # Restore binding from metadata if present.
        meta = ychat.get_metadata().get("acp_bridge")
        if meta and "harness_id" in meta:
            try:
                adapter = self.registry.get(meta["harness_id"])
                if bridge.is_draft:
                    bridge.bind(adapter)
                    pm = self.persona_managers.get(room_id)
                    if pm is not None:
                        pm.default_persona_id = None
            except HarnessNotFoundError:
                pass
        if self.router is not None:
            self.router.observe_chat_msg(room_id, self._make_msg_handler(room_id))

    def _make_msg_handler(self, room_id: str):
        def handler(rid: str, message: Any) -> None:
            bridge = self.bridge_manager.lookup(rid)
            if bridge is None or not bridge.is_bound:
                return
            # Skip if the message @-mentions a non-harness persona; persona-manager
            # will handle it.
            mentions = getattr(message, "mentions", None) or []
            pm = self.persona_managers.get(rid)
            if pm is not None and any(m in pm.personas for m in mentions):
                return
            asyncio.create_task(bridge.dispatch_message(message))
        return handler

    def bind_chat(self, room_id: str, harness_id: str) -> Any:
        """Bind a chat to a harness and suppress persona-manager auto-reply."""
        adapter = self.registry.get(harness_id)
        bridge = self.bridge_manager.get_or_create(room_id)
        bridge.bind(adapter)
        pm = self.persona_managers.get(room_id)
        if pm is not None:
            pm.default_persona_id = None
        return bridge
