import json

import pytest
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.registry import HarnessRegistry
from jupyter_ai_acp_bridge.manager import BridgeManager
from jupyter_ai_acp_bridge.handlers import HarnessesHandler


class HarnessesHandlerTest(AsyncHTTPTestCase):
    def get_app(self) -> Application:
        registry = HarnessRegistry()
        registry.register(HarnessAdapter(
            id="claude-code", display_name="Claude Code", icon="claude.svg",
            executable_factory=lambda: ["claude-code-acp"],
        ))
        return Application(
            [(r"/harnesses", HarnessesHandler, dict(
                registry=registry, bridge_manager=BridgeManager(),
            ))]
        )

    def test_lists_harnesses(self):
        resp = self.fetch("/harnesses")
        assert resp.code == 200
        body = json.loads(resp.body)
        assert body == {
            "harnesses": [
                {"id": "claude-code", "display_name": "Claude Code", "icon": "claude.svg"}
            ]
        }
