"""Translate input strings to ACP content blocks."""
from __future__ import annotations

import re
from typing import Callable, Optional

# We emit plain dicts; the persona / acp library serializes them.
ContentBlock = dict

_MENTION_RE = re.compile(r"@(cell:[\w-]+|[\w./-]+)")


def resolve_mentions(
    text: str,
    *,
    persona_names: set[str],
    cwd: Optional[str] = None,
    file_resolver: Optional[Callable[[str], Optional[str]]] = None,
    cell_resolver: Optional[Callable[[str], Optional[dict]]] = None,
) -> list[ContentBlock]:
    """Return a list of ACP content-block dicts.

    Persona-name mentions are *not* resolved; they remain inline text so the
    server-side router can intercept them.
    """
    if not text:
        return [{"type": "text", "text": ""}]

    blocks: list[ContentBlock] = []
    cursor = 0
    for match in _MENTION_RE.finditer(text):
        name = match.group(1)
        # If it's a registered persona, leave inline.
        if name in persona_names:
            continue
        # Handle cell mentions.
        if name.startswith("cell:") and cell_resolver is not None:
            cell_id = name[len("cell:"):]
            cell_info = cell_resolver(cell_id)
            if cell_info is not None:
                if match.start() > cursor:
                    blocks.append({"type": "text", "text": text[cursor:match.start()]})
                blocks.append(
                    {
                        "type": "resource",
                        "uri": f"jupyter-cell://{cell_info['notebook_path']}#{cell_id}",
                        "text": cell_info["source"],
                    }
                )
                cursor = match.end()
                continue
        # Try file resolution.
        resolved: Optional[str] = None
        if file_resolver is not None:
            resolved = file_resolver(name)
        if resolved is None:
            continue  # unresolved -> leave inline
        if match.start() > cursor:
            blocks.append({"type": "text", "text": text[cursor:match.start()]})
        blocks.append(
            {
                "type": "resource_link",
                "uri": f"file://{resolved}",
                "name": name,
            }
        )
        cursor = match.end()
    if cursor < len(text):
        blocks.append({"type": "text", "text": text[cursor:]})

    if not blocks:
        return [{"type": "text", "text": text}]
    # Drop empty text blocks
    return [b for b in blocks if not (b["type"] == "text" and b["text"] == "")]
