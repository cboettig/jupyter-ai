"""Tornado handlers exposing bridge state via REST."""
from __future__ import annotations

import json
from typing import Any

from tornado.web import RequestHandler

from .bridge import AlreadyBoundError
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


class HarnessesHandler(_BridgeBaseHandler):
    def get(self) -> None:
        self.write_json({
            "harnesses": [
                {"id": h.id, "display_name": h.display_name, "icon": h.icon}
                for h in self.registry.list()
            ]
        })


class BindHandler(_BridgeBaseHandler):
    def post(self, chat_id: str) -> None:
        try:
            payload = json.loads(self.request.body or b"{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write_json({"error": "invalid JSON"})
            return
        harness_id = payload.get("harness_id")
        if not harness_id:
            self.set_status(400)
            self.write_json({"error": "missing harness_id"})
            return
        try:
            adapter = self.registry.get(harness_id)
        except HarnessNotFoundError:
            self.set_status(404)
            self.write_json({"error": f"unknown harness {harness_id!r}"})
            return
        bridge = self.bridge_manager.get_or_create(chat_id)
        try:
            bridge.bind(adapter)
        except AlreadyBoundError as exc:
            self.set_status(409)
            self.write_json({"error": str(exc)})
            return
        self.write_json({"harness_id": harness_id})
