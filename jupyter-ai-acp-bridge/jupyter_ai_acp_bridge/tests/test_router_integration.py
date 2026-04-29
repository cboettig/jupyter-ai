import asyncio

from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.manager import BridgeManager
from jupyter_ai_acp_bridge.registry import HarnessRegistry
from jupyter_ai_acp_bridge.router_integration import BridgeRouterIntegration


class _FakeRouter:
    def __init__(self):
        self.chat_init_observers = []
        self.chat_msg_observers: dict = {}

    def observe_chat_init(self, cb):
        self.chat_init_observers.append(cb)

    def observe_chat_msg(self, room_id, cb):
        self.chat_msg_observers.setdefault(room_id, []).append(cb)


class _FakeYChat:
    def __init__(self):
        self._meta = {}

    def get_metadata(self):
        return self._meta

    def set_metadata(self, k, v):
        self._meta[k] = v


def test_chat_init_installs_chat_msg_observer():
    router = _FakeRouter()
    integration = BridgeRouterIntegration(
        registry=HarnessRegistry(),
        bridge_manager=BridgeManager(),
        persona_managers={},
    )
    integration.attach(router)
    # Trigger chat init
    ychat = _FakeYChat()
    for cb in router.chat_init_observers:
        cb("chat-1", ychat)
    assert "chat-1" in router.chat_msg_observers


def test_chat_init_restores_binding_from_metadata():
    router = _FakeRouter()
    registry = HarnessRegistry()
    adapter = HarnessAdapter(
        id="claude-code", display_name="Claude", icon="x.svg",
        executable_factory=lambda: ["claude-code-acp"],
    )
    registry.register(adapter)
    bm = BridgeManager()
    integration = BridgeRouterIntegration(
        registry=registry, bridge_manager=bm, persona_managers={},
    )
    integration.attach(router)
    ychat = _FakeYChat()
    ychat.set_metadata("acp_bridge", {"harness_id": "claude-code"})
    for cb in router.chat_init_observers:
        cb("chat-1", ychat)
    bridge = bm.lookup("chat-1")
    assert bridge is not None
    assert bridge.is_bound
    assert bridge.harness_id == "claude-code"


class _FakePersonaManager:
    def __init__(self):
        self.default_persona_id = "jupyternaut-id"
        self.personas = {"jupyternaut-id": object()}


def test_bind_chat_suppresses_default_persona():
    pm = _FakePersonaManager()
    registry = HarnessRegistry()
    adapter = HarnessAdapter(
        id="claude-code", display_name="Claude", icon="x.svg",
        executable_factory=lambda: ["claude-code-acp"],
    )
    registry.register(adapter)
    bm = BridgeManager()
    integration = BridgeRouterIntegration(
        registry=registry,
        bridge_manager=bm,
        persona_managers={"chat-1": pm},
    )
    integration.bind_chat("chat-1", "claude-code")
    bridge = bm.lookup("chat-1")
    assert bridge is not None
    assert bridge.is_bound
    assert pm.default_persona_id is None
