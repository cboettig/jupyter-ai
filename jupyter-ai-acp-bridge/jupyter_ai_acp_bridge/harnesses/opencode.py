"""OpenCode harness adapter.

Mirrors the Claude Code adapter pattern. Subclasses `OpenCodeAcpPersona` from
`jupyter_ai_acp_client` and adds the same stub capability methods so the
bridge `/state` endpoint returns a sensible payload until real ACP RPC
plumbing for SetSessionModel/Mode/ConfigOption is added.
"""
from __future__ import annotations

from typing import Any

from jupyter_ai_acp_client.acp_personas.opencode import OpenCodeAcpPersona

from ..adapter import HarnessAdapter
from ..registry import HarnessRegistry


class OpenCodeBridgePersona(OpenCodeAcpPersona):
    """Bridge-side wrapper that adds stub capability methods.

    See `claude_code.ClaudeCodeBridgePersona` for the rationale; the same
    follow-up applies (real `SetSessionModelRequest` etc. RPC plumbing
    is deferred).
    """

    async def get_session_state(self) -> dict:
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
    return ["opencode"]


OPENCODE = HarnessAdapter(
    id="opencode",
    display_name="OpenCode",
    icon="opencode.svg",
    executable_factory=_executable_factory,
    persona_class=OpenCodeBridgePersona,
)


def register(registry: HarnessRegistry) -> None:
    registry.register(OPENCODE)
