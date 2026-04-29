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


# ---------------------------------------------------------------------------
# _make_msg_handler tests
# ---------------------------------------------------------------------------

import pytest

from .test_bridge import _AsyncFakePersona


class _Msg:
    def __init__(self, mentions=None):
        self.mentions = mentions


def _bound_integration(persona_in_pm: bool = False):
    """Build an integration with chat-1 already bound to a fake-persona harness.

    If persona_in_pm is True, registers a persona under the id "jupyternaut"
    in pm.personas so a mention of @jupyternaut suppresses dispatch.
    """
    registry = HarnessRegistry()
    adapter = HarnessAdapter(
        id="claude-code", display_name="x", icon="x.svg",
        executable_factory=lambda: ["x"],
        persona_class=_AsyncFakePersona,
    )
    registry.register(adapter)
    bm = BridgeManager()
    bridge = bm.get_or_create("chat-1")
    bridge.bind(adapter, parent=object())
    pm_personas = {"jupyternaut": object()} if persona_in_pm else {}
    pm = type("PM", (), {"default_persona_id": "jupyternaut", "personas": pm_personas})()
    integration = BridgeRouterIntegration(
        registry=registry, bridge_manager=bm, persona_managers={"chat-1": pm},
    )
    return integration, bridge


@pytest.mark.asyncio
async def test_msg_handler_dispatches_when_bound_no_mentions():
    integration, bridge = _bound_integration()
    handler = integration._make_msg_handler("chat-1")
    handler("chat-1", _Msg(mentions=[]))
    await asyncio.sleep(0.05)
    assert len(bridge.persona.processed) == 1


@pytest.mark.asyncio
async def test_msg_handler_skips_when_bridge_missing():
    integration, bridge = _bound_integration()
    integration.bridge_manager.remove("chat-1")
    handler = integration._make_msg_handler("chat-1")
    handler("chat-1", _Msg(mentions=[]))
    await asyncio.sleep(0.05)
    # bridge no longer exists; nothing to assert beyond no crash


@pytest.mark.asyncio
async def test_msg_handler_skips_when_bridge_unbound():
    registry = HarnessRegistry()
    bm = BridgeManager()
    bm.get_or_create("chat-1")  # draft state
    integration = BridgeRouterIntegration(
        registry=registry, bridge_manager=bm, persona_managers={},
    )
    handler = integration._make_msg_handler("chat-1")
    handler("chat-1", _Msg(mentions=[]))
    await asyncio.sleep(0.05)
    bridge = bm.lookup("chat-1")
    assert bridge is not None
    assert bridge.persona is None  # adapter never wrapped


@pytest.mark.asyncio
async def test_msg_handler_skips_when_persona_mentioned():
    integration, bridge = _bound_integration(persona_in_pm=True)
    handler = integration._make_msg_handler("chat-1")
    handler("chat-1", _Msg(mentions=["jupyternaut"]))
    await asyncio.sleep(0.05)
    assert len(bridge.persona.processed) == 0


@pytest.mark.asyncio
async def test_msg_handler_dispatches_when_mention_unknown():
    integration, bridge = _bound_integration(persona_in_pm=True)
    handler = integration._make_msg_handler("chat-1")
    handler("chat-1", _Msg(mentions=["other-persona"]))
    await asyncio.sleep(0.05)
    assert len(bridge.persona.processed) == 1


@pytest.mark.asyncio
async def test_msg_handler_handles_missing_mentions_attr():
    integration, bridge = _bound_integration()
    handler = integration._make_msg_handler("chat-1")
    # Plain object without `mentions`
    handler("chat-1", object())
    await asyncio.sleep(0.05)
    assert len(bridge.persona.processed) == 1


@pytest.mark.asyncio
async def test_msg_handler_handles_none_mentions():
    integration, bridge = _bound_integration()
    handler = integration._make_msg_handler("chat-1")
    handler("chat-1", _Msg(mentions=None))
    await asyncio.sleep(0.05)
    assert len(bridge.persona.processed) == 1
