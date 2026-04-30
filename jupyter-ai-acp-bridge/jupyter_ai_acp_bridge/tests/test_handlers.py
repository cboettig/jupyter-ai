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


class _IdentityIntegration:
    """Test stand-in for `BridgeRouterIntegration` that uses the supplied
    chat_id directly as the bridge key, bypassing real path resolution."""

    def resolve(self, chat_path):
        return chat_path, None


def _install_integration(app, integration):
    app.settings["jupyter-ai"] = {"acp-bridge-integration": integration}


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

        # The handler delegates path resolution + bind to an integration it
        # reads from app settings. Tests bypass real path resolution by using
        # the supplied chat_id directly as the bridge key.
        class _FakeIntegration:
            def bind_chat(_self, chat_id, harness_id):
                bridge = self.bridge_manager.get_or_create(chat_id)
                bridge.bind(registry.get(harness_id))

        app = Application(
            [(r"/chats/([^/]+)/bind", BindHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager,
            ))]
        )
        app.settings["jupyter-ai"] = {"acp-bridge-integration": _FakeIntegration()}
        return app

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
        app = Application([
            (r"/chats/([^/]+)/model", ModelHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/mode", ModeHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/config-option", ConfigOptionHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/available-commands", AvailableCommandsHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
        ])
        _install_integration(app, _IdentityIntegration())
        return app

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


class JsonErrorTests(AsyncHTTPTestCase):
    """Verifies POST handlers return 400 for malformed bodies / missing fields."""

    def get_app(self):
        registry = HarnessRegistry()
        registry.register(HarnessAdapter(
            id="claude-code", display_name="x", icon="x.svg",
            executable_factory=lambda: ["x"],
        ))
        self.bridge_manager = BridgeManager()
        return Application([
            (r"/chats/([^/]+)/bind", BindHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/model", ModelHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
        ])

    def test_bind_invalid_json_returns_400(self):
        resp = self.fetch(
            "/chats/chat-1/bind", method="POST", body=b"not json",
        )
        assert resp.code == 400

    def test_bind_missing_field_returns_400(self):
        resp = self.fetch(
            "/chats/chat-1/bind", method="POST", body=json.dumps({}),
        )
        assert resp.code == 400

    def test_model_invalid_json_returns_400(self):
        resp = self.fetch(
            "/chats/chat-1/model", method="POST", body=b"not json",
        )
        assert resp.code == 400

    def test_model_missing_field_returns_400(self):
        # Bind first
        self.fetch(
            "/chats/chat-1/bind", method="POST",
            body=json.dumps({"harness_id": "claude-code"}),
        )
        resp = self.fetch(
            "/chats/chat-1/model", method="POST", body=json.dumps({}),
        )
        assert resp.code == 400


class PersonalessBindTests(AsyncHTTPTestCase):
    """Verifies handlers respond to setter calls on bound-but-persona-less bridges."""

    def get_app(self):
        registry = HarnessRegistry()
        # Adapter intentionally has no persona_class
        registry.register(HarnessAdapter(
            id="bare", display_name="Bare", icon="x.svg",
            executable_factory=lambda: ["x"],
        ))
        self.bridge_manager = BridgeManager()
        # Pre-bind so the test endpoints can run
        bridge = self.bridge_manager.get_or_create("chat-1")
        bridge.bind(registry.get("bare"))
        app = Application([
            (r"/chats/([^/]+)/model", ModelHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/mode", ModeHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/config-option", ConfigOptionHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
        ])
        _install_integration(app, _IdentityIntegration())
        return app

    def test_set_model_on_bare_bridge_returns_409(self):
        resp = self.fetch(
            "/chats/chat-1/model", method="POST",
            body=json.dumps({"model_id": "x"}),
        )
        assert resp.code == 409

    def test_set_mode_on_bare_bridge_returns_409(self):
        resp = self.fetch(
            "/chats/chat-1/mode", method="POST",
            body=json.dumps({"mode_id": "x"}),
        )
        assert resp.code == 409

    def test_set_config_option_on_bare_bridge_returns_409(self):
        resp = self.fetch(
            "/chats/chat-1/config-option", method="POST",
            body=json.dumps({"option_id": "x", "value": "y"}),
        )
        assert resp.code == 409


class UnknownChat404Tests(AsyncHTTPTestCase):
    """Verifies the 404 messages for capability handlers include chat_id."""

    def get_app(self):
        registry = HarnessRegistry()
        return Application([
            (r"/chats/([^/]+)/model", ModelHandler, dict(
                registry=registry, bridge_manager=BridgeManager())),
        ])

    def test_unknown_chat_404_message_includes_chat_id(self):
        resp = self.fetch(
            "/chats/missing-chat/model", method="POST",
            body=json.dumps({"model_id": "x"}),
        )
        assert resp.code == 404
        body = json.loads(resp.body)
        assert "missing-chat" in body["error"]


class BindHandlerIntegrationTest(AsyncHTTPTestCase):
    def get_app(self):
        registry = HarnessRegistry()
        registry.register(HarnessAdapter(
            id="claude-code", display_name="Claude", icon="x.svg",
            executable_factory=lambda: ["x"],
        ))
        self.bridge_manager = BridgeManager()
        self.bind_calls: list = []

        class _FakeIntegration:
            def bind_chat(_self, chat_id, harness_id):
                self.bind_calls.append((chat_id, harness_id))
                bridge = self.bridge_manager.get_or_create(chat_id)
                bridge.bind(registry.get(harness_id))

        app = Application([
            (r"/chats/([^/]+)/bind", BindHandler, dict(
                registry=registry,
                bridge_manager=self.bridge_manager,
            )),
        ])
        app.settings["jupyter-ai"] = {"acp-bridge-integration": _FakeIntegration()}
        return app

    def test_bind_uses_integration_when_provided(self):
        resp = self.fetch(
            "/chats/chat-1/bind", method="POST",
            body=json.dumps({"harness_id": "claude-code"}),
        )
        assert resp.code == 200
        assert self.bind_calls == [("chat-1", "claude-code")]
