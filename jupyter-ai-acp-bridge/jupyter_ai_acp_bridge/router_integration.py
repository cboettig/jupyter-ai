"""Bridge integration with jupyter-ai-router."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from .manager import BridgeManager
from .registry import HarnessNotFoundError, HarnessRegistry


class BridgeRouterIntegration:
    """Bridges between jupyter-ai-router observers and the per-chat ChatBridge.

    Created once per Jupyter Server. `attach(router)` registers the chat-init
    observer; that observer in turn registers a per-chat msg observer when each
    chat connects.

    Note on chat identity: the router's `chat_init` and `chat_msg` callbacks
    use a `room_id` of the form `text:chat:<file-id>`. The frontend's REST
    requests, on the other hand, use the chat *path* (e.g. `foo.chat`). We
    register each `ChatBridge` under both keys so lookups by either work, and
    we maintain a `room_id -> chat_path` mapping for the msg-dispatch path.
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
        self._room_to_path: dict[str, str] = {}

    def attach(self, router: Any) -> None:
        self.router = router
        router.observe_chat_init(self._on_chat_init)

    def _resolve_chat_path(self, room_id: str, ychat: Any) -> Optional[str]:
        """Best-effort resolution of room_id -> chat path.

        The persona-manager for the room owns a `fileid_manager`; we use it to
        translate the file-id segment of the room_id to a workspace-relative
        path. Fall back to the room_id itself if anything goes wrong.
        """
        pm = self.persona_managers.get(room_id)
        if pm is not None and hasattr(pm, "fileid_manager"):
            try:
                file_id = room_id.split(":")[2]
                path = pm.fileid_manager.get_path(file_id)
                if path:
                    return path
            except Exception:
                pass
        # Fall back to whatever YChat exposes as a path/name attribute.
        for attr in ("path", "name"):
            value = getattr(ychat, attr, None)
            if isinstance(value, str) and value:
                return value
        return None

    def _on_chat_init(self, room_id: str, ychat: Any) -> None:
        bridge = self.bridge_manager.get_or_create(room_id)
        bridge.ychat = ychat

        # Register the same bridge under the chat path too, so REST handlers
        # (which receive the chat path from the frontend) hit the same
        # ChatBridge instance with `ychat` already populated.
        chat_path = self._resolve_chat_path(room_id, ychat)
        if chat_path and chat_path != room_id:
            self.bridge_manager._bridges[chat_path] = bridge  # noqa: SLF001
            self._room_to_path[room_id] = chat_path

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

    def bind_chat(self, chat_id: str, harness_id: str) -> Any:
        """Bind a chat to a harness and suppress persona-manager auto-reply.

        `chat_id` may be either a router room_id or a chat path; both are
        registered as keys in the bridge_manager by `_on_chat_init`.
        """
        adapter = self.registry.get(harness_id)
        bridge = self.bridge_manager.get_or_create(chat_id)
        bridge.bind(adapter)
        # Find the room_id for this chat to suppress the right persona-manager.
        room_id = chat_id
        if chat_id not in self.persona_managers:
            for rid, path in self._room_to_path.items():
                if path == chat_id:
                    room_id = rid
                    break
        pm = self.persona_managers.get(room_id)
        if pm is not None:
            pm.default_persona_id = None
        return bridge
