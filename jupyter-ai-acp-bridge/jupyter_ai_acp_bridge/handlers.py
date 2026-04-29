"""Tornado handlers exposing bridge state via REST."""
from __future__ import annotations

import json
from typing import Any

from tornado.web import RequestHandler

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
