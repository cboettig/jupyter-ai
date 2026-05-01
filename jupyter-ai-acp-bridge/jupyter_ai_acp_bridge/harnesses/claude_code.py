"""Claude Code harness adapter.

Wraps `ClaudeAcpPersona` from `jupyter_ai_acp_client`. Capability accessors
live in `AcpBridgeCapabilityMixin`; the underlying ACP client connection
already exposes `set_session_model` / `set_session_mode` /
`set_config_option` directly, so no raw RPC plumbing is needed here.
"""
from __future__ import annotations

from jupyter_ai_acp_client.acp_personas.claude import ClaudeAcpPersona

from .._capabilities import AcpBridgeCapabilityMixin
from ..adapter import HarnessAdapter
from ..registry import HarnessRegistry


class ClaudeCodeBridgePersona(AcpBridgeCapabilityMixin, ClaudeAcpPersona):
    """Bridge persona for Claude Code: base persona + capability mixin."""


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
