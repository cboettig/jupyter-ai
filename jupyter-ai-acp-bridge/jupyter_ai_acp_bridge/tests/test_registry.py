import pytest

from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.registry import HarnessRegistry, HarnessNotFoundError


def _make(id_: str = "x") -> HarnessAdapter:
    return HarnessAdapter(
        id=id_,
        display_name=id_.upper(),
        icon=f"{id_}.svg",
        executable_factory=lambda: [id_],
    )


def test_register_and_get():
    registry = HarnessRegistry()
    a = _make("claude-code")
    registry.register(a)
    assert registry.get("claude-code") is a


def test_get_missing_raises():
    registry = HarnessRegistry()
    with pytest.raises(HarnessNotFoundError):
        registry.get("missing")


def test_register_duplicate_raises():
    registry = HarnessRegistry()
    registry.register(_make("a"))
    with pytest.raises(ValueError):
        registry.register(_make("a"))


def test_list_returns_all():
    registry = HarnessRegistry()
    registry.register(_make("a"))
    registry.register(_make("b"))
    ids = sorted(a.id for a in registry.list())
    assert ids == ["a", "b"]
