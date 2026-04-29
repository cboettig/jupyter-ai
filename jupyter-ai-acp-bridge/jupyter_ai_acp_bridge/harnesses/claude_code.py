"""Claude Code harness adapter.

The PoC wraps `ClaudeAcpPersona` from `jupyter_ai_acp_client` and adds stub
capability methods (`get_session_state`, `set_session_*`) so the bridge's
`/state` endpoint returns a sensible payload without yet implementing the
raw ACP RPC calls for model/mode/config setting. Real RPC plumbing is a
documented follow-up.
"""
from __future__ import annotations

from typing import Any

from jupyter_ai_acp_client.acp_personas.claude import ClaudeAcpPersona

from ..adapter import HarnessAdapter
from ..registry import HarnessRegistry


class ClaudeCodeBridgePersona(ClaudeAcpPersona):
    """Bridge-side wrapper that adds stub capability methods.

    The base `ClaudeAcpPersona` already handles subprocess, ACP session, and
    slash-command capture. This subclass adds the methods the bridge expects
    for `get_state` / setter ops; the setters are currently no-ops because
    the underlying `JaiAcpClient` does not yet expose convenience helpers
    for `SetSessionModelRequest` / `SetSessionModeRequest` /
    `SetSessionConfigOptionBooleanRequest`. See follow-up TODO below.
    """

    async def get_session_state(self) -> dict:
        # TODO: read available_models / session_modes / config_options from
        # the live ACP session once we add the RPC helpers. For now, return
        # an empty capability set — the UI will hide selectors that have no
        # advertised options, which matches the spec's "ACP-driven, hide on
        # absence" pattern.
        return {
            "selected_model_id": None,
            "available_models": [],
            "selected_mode_id": None,
            "session_modes": [],
            "config_options": [],
            "available_commands": list(getattr(self, "_acp_slash_commands", []) or []),
        }

    async def set_session_model(self, model_id: str) -> None:
        # TODO: send acp.SetSessionModelRequest via client.get_connection().
        return None

    async def set_session_mode(self, mode_id: str) -> None:
        # TODO: send acp.SetSessionModeRequest via client.get_connection().
        return None

    async def set_session_config_option(self, option_id: str, value: Any) -> None:
        # TODO: send acp.SetSessionConfigOptionBooleanRequest or SelectRequest.
        return None


def _executable_factory() -> list[str]:
    # Informational only; the persona class hardcodes its own executable.
    return ["claude-agent-acp"]


CLAUDE_CODE = HarnessAdapter(
    id="claude-code",
    display_name="Claude Code",
    icon="claude-code.svg",
    executable_factory=_executable_factory,
    persona_class=ClaudeCodeBridgePersona,
)


def register(registry: HarnessRegistry) -> None:
    registry.register(CLAUDE_CODE)
