from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.manager import BridgeManager


def _adapter(id_: str = "claude-code") -> HarnessAdapter:
    return HarnessAdapter(
        id=id_,
        display_name=id_,
        icon="x.svg",
        executable_factory=lambda: [id_],
    )


def test_get_or_create_returns_same_instance_per_chat():
    mgr = BridgeManager()
    b1 = mgr.get_or_create("chat-1")
    b2 = mgr.get_or_create("chat-1")
    assert b1 is b2


def test_distinct_chats_get_distinct_bridges():
    mgr = BridgeManager()
    b1 = mgr.get_or_create("chat-1")
    b2 = mgr.get_or_create("chat-2")
    assert b1 is not b2


def test_remove_drops_bridge():
    mgr = BridgeManager()
    mgr.get_or_create("chat-1")
    mgr.remove("chat-1")
    assert mgr.lookup("chat-1") is None


def test_lookup_returns_none_if_absent():
    mgr = BridgeManager()
    assert mgr.lookup("missing") is None
