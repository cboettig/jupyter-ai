"""OpenCode harness adapter.

Mirrors the Claude Code adapter pattern. Capability accessors come from
`AcpBridgeCapabilityMixin`; the underlying ACP client connection exposes
`set_session_model` / `set_session_mode` / `set_config_option` directly.
"""
from __future__ import annotations

from jupyter_ai_acp_client.acp_personas.opencode import OpenCodeAcpPersona

from .._capabilities import AcpBridgeCapabilityMixin
from ..adapter import HarnessAdapter
from ..registry import HarnessRegistry


class OpenCodeBridgePersona(AcpBridgeCapabilityMixin, OpenCodeAcpPersona):
    """Bridge persona for OpenCode: base persona + capability mixin."""


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
