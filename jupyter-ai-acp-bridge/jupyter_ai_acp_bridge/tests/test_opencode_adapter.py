def test_adapter_id_and_class():
    from jupyter_ai_acp_bridge.harnesses.opencode import OPENCODE
    assert OPENCODE.id == "opencode"
    assert OPENCODE.display_name == "OpenCode"
    assert OPENCODE.persona_class is not None


def test_adapter_executable_factory():
    from jupyter_ai_acp_bridge.harnesses.opencode import OPENCODE
    assert OPENCODE.executable_factory() == ["opencode"]


def test_register_adds_to_registry():
    from jupyter_ai_acp_bridge.harnesses.opencode import register
    from jupyter_ai_acp_bridge.registry import HarnessRegistry
    reg = HarnessRegistry()
    register(reg)
    adapter = reg.get("opencode")
    assert adapter.id == "opencode"


def test_persona_class_is_subclass_of_opencode():
    """Catch accidental refactor breakage."""
    from jupyter_ai_acp_bridge.harnesses.opencode import OpenCodeBridgePersona
    from jupyter_ai_acp_client.acp_personas.opencode import OpenCodeAcpPersona
    assert issubclass(OpenCodeBridgePersona, OpenCodeAcpPersona)
