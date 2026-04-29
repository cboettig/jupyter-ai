import pytest

from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.bridge import ChatBridge, AlreadyBoundError, NotBoundError


def _adapter():
    return HarnessAdapter(
        id="claude-code",
        display_name="Claude Code",
        icon="x.svg",
        executable_factory=lambda: ["claude-code-acp"],
    )


def test_initial_state_is_draft():
    bridge = ChatBridge(chat_id="chat-1")
    assert bridge.is_draft
    assert not bridge.is_bound
    assert bridge.harness_id is None


def test_bind_transitions_to_bound():
    bridge = ChatBridge(chat_id="chat-1")
    bridge.bind(_adapter())
    assert bridge.is_bound
    assert not bridge.is_draft
    assert bridge.harness_id == "claude-code"


def test_double_bind_raises():
    bridge = ChatBridge(chat_id="chat-1")
    bridge.bind(_adapter())
    with pytest.raises(AlreadyBoundError):
        bridge.bind(_adapter())


def test_state_query_when_unbound_raises():
    bridge = ChatBridge(chat_id="chat-1")
    with pytest.raises(NotBoundError):
        bridge.adapter


class _FakeYChat:
    def __init__(self) -> None:
        self._meta: dict = {}

    def get_metadata(self) -> dict:
        return self._meta

    def set_metadata(self, key: str, value) -> None:
        self._meta[key] = value


def test_bind_writes_metadata():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    bridge.bind(_adapter())
    assert ychat.get_metadata().get("acp_bridge") == {"harness_id": "claude-code"}


def test_construct_with_existing_metadata_restores_binding():
    ychat = _FakeYChat()
    ychat.set_metadata("acp_bridge", {"harness_id": "claude-code"})
    from jupyter_ai_acp_bridge.registry import HarnessRegistry
    registry = HarnessRegistry()
    registry.register(_adapter())
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat, registry=registry)
    assert bridge.is_bound
    assert bridge.harness_id == "claude-code"


class _FakePersona:
    last_kwargs: dict = {}

    def __init__(self, *, parent=None, ychat=None, executable=None, **kwargs):
        _FakePersona.last_kwargs = {
            "parent": parent,
            "ychat": ychat,
            "executable": executable,
            **kwargs,
        }
        self.parent = parent
        self.ychat = ychat


def test_bind_instantiates_persona():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    adapter = HarnessAdapter(
        id="claude-code",
        display_name="Claude Code",
        icon="x.svg",
        executable_factory=lambda: ["claude-code-acp"],
        persona_class=_FakePersona,
    )
    bridge.bind(adapter, parent=object())
    assert bridge.persona is not None
    assert bridge.persona.ychat is ychat
    assert _FakePersona.last_kwargs.get("executable") == ["claude-code-acp"]


def test_bind_without_persona_class_keeps_persona_none():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    adapter = _adapter()  # no persona_class
    bridge.bind(adapter, parent=object())
    assert bridge.persona is None


import asyncio


class _AsyncFakePersona:
    """A fake persona that records what was called."""

    def __init__(self, *, parent=None, ychat=None, executable=None, **kwargs):
        self.processed: list = []
        self.model_set: list = []
        self.mode_set: list = []
        self.config_set: list = []

    async def process_message(self, message):
        self.processed.append(message)

    async def get_session_state(self):
        return {
            "selected_model_id": "sonnet-4-5",
            "available_models": [{"id": "sonnet-4-5", "name": "Sonnet 4.5"}],
            "selected_mode_id": "default",
            "session_modes": [{"id": "default", "name": "Default"}],
            "config_options": [],
            "available_commands": [{"name": "/help", "description": "help"}],
        }

    async def set_session_model(self, model_id):
        self.model_set.append(model_id)

    async def set_session_mode(self, mode_id):
        self.mode_set.append(mode_id)

    async def set_session_config_option(self, option_id, value):
        self.config_set.append((option_id, value))


def test_dispatch_message_calls_persona():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    adapter = HarnessAdapter(
        id="claude-code",
        display_name="x",
        icon="x.svg",
        executable_factory=lambda: ["x"],
        persona_class=_AsyncFakePersona,
    )
    bridge.bind(adapter, parent=object())
    msg = object()
    asyncio.run(bridge.dispatch_message(msg))
    assert bridge.persona.processed == [msg]


def test_set_model_delegates():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    adapter = HarnessAdapter(
        id="claude-code",
        display_name="x",
        icon="x.svg",
        executable_factory=lambda: ["x"],
        persona_class=_AsyncFakePersona,
    )
    bridge.bind(adapter, parent=object())
    asyncio.run(bridge.set_model("opus-4"))
    assert bridge.persona.model_set == ["opus-4"]


def test_get_state_returns_dict_when_bound():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    adapter = HarnessAdapter(
        id="claude-code",
        display_name="x",
        icon="x.svg",
        executable_factory=lambda: ["x"],
        persona_class=_AsyncFakePersona,
    )
    bridge.bind(adapter, parent=object())
    state = asyncio.run(bridge.get_state())
    assert state["harness_id"] == "claude-code"
    assert state["selected_model_id"] == "sonnet-4-5"
    assert any(m["id"] == "sonnet-4-5" for m in state["available_models"])


def test_get_state_when_unbound():
    bridge = ChatBridge(chat_id="chat-1")
    state = asyncio.run(bridge.get_state())
    assert state == {"harness_id": None}
