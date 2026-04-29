def test_adapter_id_and_class():
    from jupyter_ai_acp_bridge.harnesses.claude_code import CLAUDE_CODE
    assert CLAUDE_CODE.id == "claude-code"
    assert CLAUDE_CODE.display_name == "Claude Code"
    assert CLAUDE_CODE.persona_class is not None


def test_adapter_executable_factory():
    from jupyter_ai_acp_bridge.harnesses.claude_code import CLAUDE_CODE
    assert CLAUDE_CODE.executable_factory() == ["claude-agent-acp"]


def test_register_adds_to_registry():
    from jupyter_ai_acp_bridge.harnesses.claude_code import register
    from jupyter_ai_acp_bridge.registry import HarnessRegistry
    reg = HarnessRegistry()
    register(reg)
    adapter = reg.get("claude-code")
    assert adapter.id == "claude-code"
