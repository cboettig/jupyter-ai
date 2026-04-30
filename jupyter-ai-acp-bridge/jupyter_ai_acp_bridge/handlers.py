"""Tornado handlers exposing bridge state via REST."""
from __future__ import annotations

import json
from typing import Any, Optional

from tornado.web import RequestHandler

from .bridge import AlreadyBoundError, NotBoundError
from .manager import BridgeManager
from .registry import HarnessNotFoundError, HarnessRegistry


class _BridgeBaseHandler(RequestHandler):
    def initialize(
        self, registry: HarnessRegistry, bridge_manager: BridgeManager
    ) -> None:
        self.registry = registry
        self.bridge_manager = bridge_manager

    @property
    def integration(self) -> Any:
        return self.settings.get("jupyter-ai", {}).get("acp-bridge-integration")

    def lookup_bridge(self, chat_path: str) -> Any:
        """Resolve a frontend chat_path to the bridge, going via the
        integration's `resolve()` method (which translates path -> room_id)."""
        if self.integration is None:
            return None
        room_id, _ychat = self.integration.resolve(chat_path)
        if room_id is None:
            return None
        return self.bridge_manager.lookup(room_id)

    def write_json(self, payload: Any) -> None:
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(payload))

    def parse_json_body(self, required: tuple[str, ...] = ()) -> dict | None:
        try:
            payload = json.loads(self.request.body or b"{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write_json({"error": "invalid JSON"})
            return None
        for key in required:
            if key not in payload:
                self.set_status(400)
                self.write_json({"error": f"missing {key}"})
                return None
        return payload


class HarnessesHandler(_BridgeBaseHandler):
    def get(self) -> None:
        self.write_json({
            "harnesses": [
                {"id": h.id, "display_name": h.display_name, "icon": h.icon}
                for h in self.registry.list()
            ]
        })


class BindHandler(_BridgeBaseHandler):
    @property
    def integration(self) -> Any:
        # Look up at request time from app settings, so the integration
        # becomes visible to handlers as soon as `_setup_router_integration`
        # finishes (which happens asynchronously after extension init).
        return self.settings.get("jupyter-ai", {}).get("acp-bridge-integration")

    def post(self, chat_id: str) -> None:
        payload = self.parse_json_body(required=("harness_id",))
        if payload is None:
            return
        harness_id = payload["harness_id"]
        try:
            self.registry.get(harness_id)
        except HarnessNotFoundError:
            self.set_status(404)
            self.write_json({"error": f"unknown harness {harness_id!r}"})
            return
        if self.integration is None:
            # Fail loudly: a bind that bypasses the integration would create a
            # bridge with no ychat, which crashes downstream when persona
            # initialization tries to read ychat.awareness.
            self.set_status(503)
            self.write_json({
                "error": (
                    "ACP bridge integration not yet attached. "
                    "Wait a moment and retry, or check the server log."
                )
            })
            return
        try:
            self.integration.bind_chat(chat_id, harness_id)
        except AlreadyBoundError as exc:
            self.set_status(409)
            self.write_json({"error": str(exc)})
            return
        except RuntimeError as exc:
            self.set_status(404)
            self.write_json({"error": str(exc)})
            return
        self.write_json({"harness_id": harness_id})


class StateHandler(_BridgeBaseHandler):
    async def get(self, chat_id: str) -> None:
        bridge = self.lookup_bridge(chat_id)
        if bridge is None:
            self.write_json({"harness_id": None})
            return
        state = await bridge.get_state()
        self.write_json(state)


class ModelHandler(_BridgeBaseHandler):
    async def post(self, chat_id: str) -> None:
        payload = self.parse_json_body(required=("model_id",))
        if payload is None:
            return
        bridge = self.lookup_bridge(chat_id)
        if bridge is None or not bridge.is_bound:
            self.set_status(404)
            self.write_json({"error": f"chat {chat_id!r} has no harness bound"})
            return
        try:
            await bridge.set_model(payload["model_id"])
        except NotBoundError as exc:
            self.set_status(409)
            self.write_json({"error": str(exc)})
            return
        self.write_json({"ok": True})


class ModeHandler(_BridgeBaseHandler):
    async def post(self, chat_id: str) -> None:
        payload = self.parse_json_body(required=("mode_id",))
        if payload is None:
            return
        bridge = self.lookup_bridge(chat_id)
        if bridge is None or not bridge.is_bound:
            self.set_status(404)
            self.write_json({"error": f"chat {chat_id!r} has no harness bound"})
            return
        try:
            await bridge.set_mode(payload["mode_id"])
        except NotBoundError as exc:
            self.set_status(409)
            self.write_json({"error": str(exc)})
            return
        self.write_json({"ok": True})


class ConfigOptionHandler(_BridgeBaseHandler):
    async def post(self, chat_id: str) -> None:
        payload = self.parse_json_body(required=("option_id", "value"))
        if payload is None:
            return
        bridge = self.lookup_bridge(chat_id)
        if bridge is None or not bridge.is_bound:
            self.set_status(404)
            self.write_json({"error": f"chat {chat_id!r} has no harness bound"})
            return
        try:
            await bridge.set_config_option(payload["option_id"], payload["value"])
        except NotBoundError as exc:
            self.set_status(409)
            self.write_json({"error": str(exc)})
            return
        self.write_json({"ok": True})


class AvailableCommandsHandler(_BridgeBaseHandler):
    async def get(self, chat_id: str) -> None:
        bridge = self.lookup_bridge(chat_id)
        if bridge is None or not bridge.is_bound:
            self.write_json({"commands": []})
            return
        state = await bridge.get_state()
        self.write_json({"commands": state.get("available_commands", [])})
