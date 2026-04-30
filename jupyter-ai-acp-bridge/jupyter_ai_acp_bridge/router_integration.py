"""Bridge integration with jupyter-ai-router and jupyter-ai-persona-manager.

Chat-identity resolution is handled exactly the way `jupyter-ai-acp-client`
does it: the frontend sends `chat_path`; the backend translates that to a
`file_id` via the `file_id_manager`, synthesizes the canonical `room_id` as
`text:chat:<file_id>`, and looks up the per-chat persona-manager (which
owns the `YChat` instance). This is the only resolution path; no caching,
no fallbacks. The chat-init observer is used only to restore a binding
from chat metadata when a chat reopens.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from jupyter_ai_persona_manager.persona_manager import (
    SYSTEM_USERNAME,
    is_persona,
)

from .manager import BridgeManager
from .registry import HarnessNotFoundError, HarnessRegistry


class BridgeRouterIntegration:
    def __init__(
        self,
        *,
        registry: HarnessRegistry,
        bridge_manager: BridgeManager,
        persona_managers: dict[str, Any],
        file_id_manager: Any = None,
    ) -> None:
        self.registry = registry
        self.bridge_manager = bridge_manager
        self.persona_managers = persona_managers
        self.file_id_manager = file_id_manager
        self.router: Any = None

    def attach(self, router: Any) -> None:
        self.router = router
        router.observe_chat_init(self._on_chat_init)

    def resolve(self, chat_path: str) -> tuple[Optional[str], Optional[Any]]:
        """Resolve a frontend-supplied chat path to (room_id, ychat).

        Mirrors the resolution used in `jupyter-ai-acp-client`'s routes:
        chat_path -> file_id (via file_id_manager) -> room_id `text:chat:<id>`
        -> persona_manager (which owns the YChat).
        """
        if self.file_id_manager is None:
            return None, None
        try:
            file_id = self.file_id_manager.get_id(chat_path)
        except Exception:
            return None, None
        if not file_id:
            return None, None
        room_id = f"text:chat:{file_id}"
        pm = self.persona_managers.get(room_id)
        if pm is None:
            return None, None
        return room_id, getattr(pm, "ychat", None)

    def _on_chat_init(self, room_id: str, ychat: Any) -> None:
        """Restore a previously-bound harness on chat reopen, and install
        the per-chat msg observer."""
        bridge = self.bridge_manager.get_or_create(room_id)
        bridge.ychat = ychat

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
            # Mirror PersonaManager.on_chat_message: never dispatch a message
            # whose sender is a persona or the system. Without this, the
            # persona's own replies loop back as user prompts, corrupting the
            # conversation and eventually triggering Anthropic's
            # "cache_control cannot be set for empty text blocks" 400.
            sender = getattr(message, "sender", "") or ""
            if is_persona(sender) or sender == SYSTEM_USERNAME:
                return
            mentions = getattr(message, "mentions", None) or []
            pm = self.persona_managers.get(rid)
            if pm is not None and any(m in pm.personas for m in mentions):
                return
            asyncio.create_task(bridge.dispatch_message(message))
        return handler

    def bind_chat(self, chat_path: str, harness_id: str) -> Any:
        """Bind a chat (looked up by frontend chat path) to a harness."""
        adapter = self.registry.get(harness_id)
        room_id, ychat = self.resolve(chat_path)
        if room_id is None or ychat is None:
            raise RuntimeError(
                f"Chat {chat_path!r} is not initialized. Open it once and retry."
            )
        bridge = self.bridge_manager.get_or_create(room_id)
        bridge.ychat = ychat
        pm = self.persona_managers.get(room_id)
        # Persona must be parented to its PersonaManager so it can resolve
        # event_loop, log, fileid_manager, etc. via `self.parent.<attr>`.
        bridge.bind(adapter, parent=pm)
        if pm is not None:
            pm.default_persona_id = None
        return bridge
