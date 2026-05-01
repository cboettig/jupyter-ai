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
from dataclasses import replace
from typing import Any, Optional

from jupyter_ai_persona_manager.persona_manager import (
    SYSTEM_USERNAME,
    is_persona,
)

from .manager import BridgeManager
from .registry import HarnessNotFoundError, HarnessRegistry

# Module prefix for the upstream `jupyter-ai-acp-client` @-mention personas.
# When the bridge is installed, those personas are superseded by bridge-bound
# chats (see `_suppress_acp_client_personas`); both paths spawn the same
# claude-agent-acp subprocess, so keeping both registered is just confusing.
_ACP_CLIENT_PERSONAS_MODULE = "jupyter_ai_acp_client.acp_personas"


def _prune_acp_client_persona_classes() -> None:
    """Remove acp-client entries from `PersonaManager._ep_persona_classes`
    (a ClassVar) so future PersonaManager instances skip them at
    `_init_personas()` time — preventing fresh chats from instantiating
    and registering them as YChat users in the first place.

    Safe to call before the cache is populated (returns silently);
    idempotent once it's pruned. Once any chat has been opened the cache
    is populated and the prune sticks for the rest of the process.
    """
    try:
        from jupyter_ai_persona_manager.persona_manager import PersonaManager
    except ImportError:
        return
    classes = PersonaManager._ep_persona_classes
    if not isinstance(classes, list):
        return
    PersonaManager._ep_persona_classes = [
        c
        for c in classes
        if not (
            (cls := c.get("persona_class")) is not None
            and getattr(cls, "__module__", "").startswith(
                _ACP_CLIENT_PERSONAS_MODULE
            )
        )
    ]


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

    def _suppress_acp_client_personas(self, pm: Any) -> None:
        """Remove auto-discovered `jupyter-ai-acp-client` personas so they
        don't appear in routing OR in @-mention completion. The bridge
        supersedes them; same subprocess, single canonical entry path.

        Three places to clean up:
          1. `PersonaManager._ep_persona_classes` (class-level cache):
             prune the acp-client entries so *future* PersonaManager
             instances (i.e. new chats opened later) don't even
             instantiate them. Each persona class's `__init__` calls
             `ychat.set_user()`, so preventing instantiation is the only
             way to keep the YChat user list clean for fresh chats.
          2. `pm.personas` (this PM): kills the dispatch path. Without
             this `@Claude` would still route through `on_chat_message`'s
             mention dispatch even after we hide it from the picker.
          3. `pm.ychat._yusers` (this PM): kills the @-mention
             completion for this already-open chat. Each persona
             registered itself as a YChat user during instantiation;
             popping from `_yusers` removes the entry from the dropdown.
             Note this only sticks on the *current* chat — if the user
             reloads, Y-doc state may resync the entry from peers; (1)
             prevents new instantiations from re-adding.

        Idempotent — safe to call repeatedly.
        """
        # Step 0: prune the class-level cache once. Cheap to re-run; the
        # filter is a no-op once the entries are already gone.
        _prune_acp_client_persona_classes()

        if pm is None:
            return
        # Step 1: drop from pm.personas. While we're walking, collect the
        # ids of personas we're suppressing so we can also strip them
        # from the YChat user list.
        suppressed_ids: list[str] = []
        if hasattr(pm, "personas"):
            for pid, persona in list(pm.personas.items()):
                if type(persona).__module__.startswith(
                    _ACP_CLIENT_PERSONAS_MODULE
                ):
                    suppressed_ids.append(pid)
                    pm.personas.pop(pid, None)
        # Step 2: drop those ids from ychat._yusers. Best-effort: if
        # YChat changes its internal storage we just log and move on.
        ychat = getattr(pm, "ychat", None)
        yusers = getattr(ychat, "_yusers", None)
        if yusers is None:
            return
        for pid in suppressed_ids:
            try:
                if pid in yusers:
                    del yusers[pid]
            except Exception:
                # Don't let a failed user-pop block the bind.
                pass

    def _on_chat_init(self, room_id: str, ychat: Any) -> None:
        """Install the per-chat msg observer and schedule restore-from-
        metadata. The actual rebind is deferred to the next event-loop
        tick because the router fires its `chat_init` observers in
        registration order, and `jupyter-ai-persona-manager`'s observer
        (which writes `persona_managers[room_id]`) runs *after* ours —
        so calling `persona_managers.get(room_id)` synchronously here
        always returns None on the very first chat-init for that room.

        Also subscribes to YChat metadata changes: if the Y-doc was
        reset on this connect (the chat extension logs "Clearing YDoc
        source before handshake" when client/server disagree), the
        first restore attempt will see empty metadata; we re-attempt
        each time metadata changes until the binding takes.
        """
        bridge = self.bridge_manager.get_or_create(room_id)
        bridge.ychat = ychat

        if self.router is not None:
            self.router.observe_chat_msg(room_id, self._make_msg_handler(room_id))
            # The router routes `/`-prefixed messages to slash_cmd_observers
            # ONLY, not chat_msg_observers — so without this second
            # registration, every `/help`, `/mode plan`, `/<skill-name>`
            # the user submits would be silently dropped from the bridge's
            # perspective. We register a wildcard pattern that the
            # handler then filters down to commands the bound agent
            # actually advertises (so we don't double-handle
            # `/refresh-personas` etc. that other extensions own).
            self.router.observe_slash_cmd_msg(
                room_id, ".*", self._make_slash_msg_handler(room_id)
            )

        try:
            asyncio.get_event_loop().call_soon(
                self._restore_binding_from_metadata, room_id, ychat
            )
        except RuntimeError:
            # No running loop — invoke synchronously and accept that the
            # parent reference may be missing.
            self._restore_binding_from_metadata(room_id, ychat)

        # Subscribe to metadata changes: idempotent retry when metadata
        # arrives via Yjs sync after our first attempt. Defer the actual
        # restore work to the next event-loop tick — the observer fires
        # synchronously inside the Yjs transaction, and our bind path
        # itself calls `ychat.set_metadata(...)`, which would otherwise
        # recursively re-enter the observer mid-transaction. Doing the
        # work post-tick lets the transaction complete first.
        try:
            ymeta = getattr(ychat, "_ymetadata", None)
            if ymeta is not None and hasattr(ymeta, "observe"):
                def _on_metadata_change(_event: Any) -> None:
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        return
                    loop.call_soon(
                        self._restore_binding_from_metadata, room_id, ychat
                    )
                ymeta.observe(_on_metadata_change)
        except Exception:
            # If we can't subscribe, the deferred restore is the only
            # attempt. Fail open.
            pass

    def _restore_binding_from_metadata(self, room_id: str, ychat: Any) -> None:
        """Look up `acp_bridge.harness_id` in chat metadata and rebind.

        Runs deferred from `_on_chat_init` so peer extensions have had
        a chance to populate their state for this room (specifically,
        `persona_managers[room_id]`). Idempotent — returns early when
        metadata isn't yet populated, when the harness is unknown, or
        when the bridge is already bound.
        """
        try:
            pm = self.persona_managers.get(room_id)
            self._suppress_acp_client_personas(pm)

            meta = ychat.get_metadata().get("acp_bridge") if ychat is not None else None
            if not (meta and "harness_id" in meta):
                return
            try:
                adapter = self.registry.get(meta["harness_id"])
            except HarnessNotFoundError:
                return
            bridge = self.bridge_manager.get_or_create(room_id)
            if not bridge.is_draft:
                return
            # Persona must be parented to its PersonaManager so it can
            # resolve event_loop, log, fileid_manager via `self.parent.<attr>`.
            bridge.bind(adapter, parent=pm)
            if pm is not None:
                pm.default_persona_id = None
        except Exception:
            import logging
            logging.getLogger("ServerApp").exception(
                "[acp-bridge] _restore_binding crashed for %s", room_id
            )

    def _make_slash_msg_handler(self, room_id: str):
        """Re-route slash-prefixed messages back to the bound persona.

        The router strips the `/<command>` prefix before invoking us
        (callback signature: `(rid, command, trimmed_message)`). To make
        the agent see the original text — claude-agent-acp's slash-skill
        loader expects the literal `/<command>` at the start of the
        prompt — we reconstruct the body before dispatch.

        Filters down to commands the *bound persona* actually advertises
        in its `_acp_slash_commands`. Without this filter the wildcard
        pattern `.*` would forward `/refresh-personas` (jupyter-ai's
        built-in) and similar to the agent, which would just confuse it.
        """
        def handler(rid: str, command: str, message: Any) -> None:
            bridge = self.bridge_manager.lookup(rid)
            if bridge is None or not bridge.is_bound:
                return
            sender = getattr(message, "sender", "") or ""
            if is_persona(sender) or sender == SYSTEM_USERNAME:
                return
            persona = getattr(bridge, "_persona", None)
            if persona is None:
                return
            agent_commands = getattr(persona, "_acp_slash_commands", []) or []
            if not any(getattr(c, "name", None) == command for c in agent_commands):
                # Not an agent-advertised slash command — let whoever
                # else owns this pattern (e.g. jupyter-ai's
                # `/refresh-personas`) handle it.
                return
            rest = getattr(message, "body", "") or ""
            original_body = "/" + command + ((" " + rest) if rest else "")
            try:
                rebuilt = replace(message, body=original_body)
            except Exception:
                # If `message` isn't a dataclass for some reason, fall
                # back to mutating in-place.
                message.body = original_body
                rebuilt = message
            asyncio.create_task(bridge.dispatch_message(rebuilt))
        return handler

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
        # Idempotent — _on_chat_init usually got there first, but a chat
        # bound before its init observer fires would still benefit.
        self._suppress_acp_client_personas(pm)
        return bridge
