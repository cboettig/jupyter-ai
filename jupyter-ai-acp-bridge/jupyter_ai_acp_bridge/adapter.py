"""HarnessAdapter dataclass."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class HarnessAdapter:
    """Static metadata for an ACP harness wired to the bridge.

    Intentionally narrow: no model lists, no effort levels, no mode names.
    Everything dynamic comes from the live ACP session.
    """

    id: str
    display_name: str
    icon: str
    executable_factory: Callable[[], list[str]]
    env: Optional[dict[str, str]] = None
    persona_class: Optional[type] = None
