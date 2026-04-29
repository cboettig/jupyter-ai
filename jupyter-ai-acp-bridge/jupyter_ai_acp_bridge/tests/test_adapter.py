from jupyter_ai_acp_bridge.adapter import HarnessAdapter


def test_harness_adapter_required_fields():
    adapter = HarnessAdapter(
        id="claude-code",
        display_name="Claude Code",
        icon="claude.svg",
        executable_factory=lambda: ["claude-code-acp"],
    )
    assert adapter.id == "claude-code"
    assert adapter.display_name == "Claude Code"
    assert adapter.icon == "claude.svg"
    assert adapter.executable_factory() == ["claude-code-acp"]
    assert adapter.env is None
    assert adapter.persona_class is None


def test_harness_adapter_with_persona_class():
    class StubPersona:
        pass

    adapter = HarnessAdapter(
        id="x",
        display_name="X",
        icon="x.svg",
        executable_factory=lambda: ["x"],
        env={"FOO": "bar"},
        persona_class=StubPersona,
    )
    assert adapter.env == {"FOO": "bar"}
    assert adapter.persona_class is StubPersona
