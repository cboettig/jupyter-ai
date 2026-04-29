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
