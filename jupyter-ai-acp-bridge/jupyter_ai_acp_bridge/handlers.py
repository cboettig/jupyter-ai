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
    def initialize(
        self,
        registry: HarnessRegistry,
        bridge_manager: BridgeManager,
        integration: Optional[Any] = None,
    ) -> None:
        super().initialize(registry, bridge_manager)
        self.integration = integration

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
        try:
            if self.integration is not None:
                self.integration.bind_chat(chat_id, harness_id)
            else:
                bridge = self.bridge_manager.get_or_create(chat_id)
                bridge.bind(self.registry.get(harness_id))
        except AlreadyBoundError as exc:
            self.set_status(409)
            self.write_json({"error": str(exc)})
            return
        self.write_json({"harness_id": harness_id})


class StateHandler(_BridgeBaseHandler):
    async def get(self, chat_id: str) -> None:
        bridge = self.bridge_manager.lookup(chat_id)
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
        bridge = self.bridge_manager.lookup(chat_id)
        if bridge is None:
            self.set_status(404)
            self.write_json({"error": f"chat {chat_id!r} has no bridge"})
            return
        if not bridge.is_bound:
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
        bridge = self.bridge_manager.lookup(chat_id)
        if bridge is None:
            self.set_status(404)
            self.write_json({"error": f"chat {chat_id!r} has no bridge"})
            return
        if not bridge.is_bound:
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
        bridge = self.bridge_manager.lookup(chat_id)
        if bridge is None:
            self.set_status(404)
            self.write_json({"error": f"chat {chat_id!r} has no bridge"})
            return
        if not bridge.is_bound:
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
        bridge = self.bridge_manager.lookup(chat_id)
        if bridge is None or not bridge.is_bound:
            self.write_json({"commands": []})
            return
        state = await bridge.get_state()
        self.write_json({"commands": state.get("available_commands", [])})
