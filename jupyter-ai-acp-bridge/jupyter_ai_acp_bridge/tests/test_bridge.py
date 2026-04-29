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
