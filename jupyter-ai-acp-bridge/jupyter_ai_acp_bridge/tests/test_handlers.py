import json

import pytest
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.registry import HarnessRegistry
from jupyter_ai_acp_bridge.manager import BridgeManager
from jupyter_ai_acp_bridge.handlers import (
    HarnessesHandler,
    BindHandler,
    StateHandler,
    ModelHandler,
    ModeHandler,
    ConfigOptionHandler,
    AvailableCommandsHandler,
)
from jupyter_ai_acp_bridge.tests.test_bridge import _AsyncFakePersona


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


class BindHandlerTest(AsyncHTTPTestCase):
    def get_app(self):
        registry = HarnessRegistry()
        registry.register(HarnessAdapter(
            id="claude-code", display_name="Claude Code", icon="x.svg",
            executable_factory=lambda: ["x"],
        ))
        self.bridge_manager = BridgeManager()
        return Application(
            [(r"/chats/([^/]+)/bind", BindHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager,
            ))]
        )

    def test_bind_creates_binding(self):
        resp = self.fetch(
            "/chats/chat-1/bind",
            method="POST",
            body=json.dumps({"harness_id": "claude-code"}),
        )
        assert resp.code == 200
        body = json.loads(resp.body)
        assert body["harness_id"] == "claude-code"

    def test_bind_unknown_harness_returns_404(self):
        resp = self.fetch(
            "/chats/chat-1/bind",
            method="POST",
            body=json.dumps({"harness_id": "nope"}),
        )
        assert resp.code == 404

    def test_double_bind_returns_409(self):
        self.fetch(
            "/chats/chat-1/bind", method="POST",
            body=json.dumps({"harness_id": "claude-code"}),
        )
        resp = self.fetch(
            "/chats/chat-1/bind", method="POST",
            body=json.dumps({"harness_id": "claude-code"}),
        )
        assert resp.code == 409


class StateHandlerTest(AsyncHTTPTestCase):
    def get_app(self):
        registry = HarnessRegistry()
        self.bridge_manager = BridgeManager()
        return Application(
            [(r"/chats/([^/]+)/state", StateHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager,
            ))]
        )

    def test_unbound_returns_null(self):
        resp = self.fetch("/chats/chat-1/state")
        assert resp.code == 200
        body = json.loads(resp.body)
        assert body == {"harness_id": None}


class CapabilityHandlerTests(AsyncHTTPTestCase):
    def get_app(self):
        registry = HarnessRegistry()
        adapter = HarnessAdapter(
            id="claude-code", display_name="x", icon="x.svg",
            executable_factory=lambda: ["x"],
            persona_class=_AsyncFakePersona,
        )
        registry.register(adapter)
        self.bridge_manager = BridgeManager()
        # Pre-bind chat-1
        bridge = self.bridge_manager.get_or_create("chat-1")
        bridge.bind(adapter, parent=object())
        self.bridge = bridge
        return Application([
            (r"/chats/([^/]+)/model", ModelHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/mode", ModeHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/config-option", ConfigOptionHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/available-commands", AvailableCommandsHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
        ])

    def test_set_model(self):
        resp = self.fetch(
            "/chats/chat-1/model", method="POST",
            body=json.dumps({"model_id": "opus-4"}),
        )
        assert resp.code == 200
        assert self.bridge.persona.model_set == ["opus-4"]

    def test_set_mode(self):
        resp = self.fetch(
            "/chats/chat-1/mode", method="POST",
            body=json.dumps({"mode_id": "plan"}),
        )
        assert resp.code == 200
        assert self.bridge.persona.mode_set == ["plan"]

    def test_set_config_option(self):
        resp = self.fetch(
            "/chats/chat-1/config-option", method="POST",
            body=json.dumps({"option_id": "verbose", "value": True}),
        )
        assert resp.code == 200
        assert self.bridge.persona.config_set == [("verbose", True)]

    def test_available_commands(self):
        resp = self.fetch("/chats/chat-1/available-commands")
        assert resp.code == 200
        body = json.loads(resp.body)
        assert body["commands"] == [{"name": "/help", "description": "help"}]
