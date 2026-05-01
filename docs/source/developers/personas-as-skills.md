# Personas as Skills

*A note on how the per-thread harness binding work in this fork sits
inside the original Personas vision, and a friendly suggestion for how
that vision might align with where the broader open agent ecosystem
is going.*

This is companion reading for [issue #1558](https://github.com/jupyterlab/jupyter-ai/issues/1558)
and the [ACP bridge design spec](../../superpowers/specs/2026-04-28-acp-bridge-design.md).
It's about *concepts*, not code — the goal is to put names on three
things that have been quietly co-existing inside "I'm chatting with an
AI" and to suggest where each belongs.

## The Personas vision is right

The Personas surface in `jupyter-ai-persona-manager` was a strong
design call. It frames the right thing: the user should be able to
shape *per-thread* context — system prompt, tools, behavior, identity —
without that shaping leaking across other conversations. That framing
predates ACP and the recent wave of "agent" tooling, and it still
holds up.

This document doesn't argue against Personas. It argues that the
*implementation surface* for defining one is now living happily in the
open AI ecosystem under a different name, and that Jupyter AI can
benefit from meeting it there.

## Three things that are sometimes one thing

Inside any "I'm chatting with an AI" interaction there are at least
three independent axes:

| Axis | Examples |
|---|---|
| **Model** — which LLM is doing inference | Sonnet 4.6, Haiku 4.5, GPT-5.5, Gemini 3 Pro… |
| **Harness** — which agent runtime is mediating tool use, file I/O, MCP, slash dispatch, multi-turn loops | Claude Code (`claude-agent-acp`), OpenCode, Codex, Goose, Gemini-CLI… |
| **Persona** — what bundle of *context* the user has adopted for this conversation | "Senior data scientist", "Strict code reviewer", "Field biologist studying salmon", … |

These are orthogonal. You can run the same persona against a different
model or harness; you can swap models and modes without changing
persona; and you can want the same persona across totally different
chat surfaces (Jupyter, terminal, IDE, …).

The trouble starts when an interface conflates two of them. The
two specific conflations worth naming:

1. **Persona ↔ harness.** "`@claude` is a persona" implicitly equates
   the harness (claude-agent-acp) with a persona identity. Switching
   harnesses means abandoning the persona; defining a persona requires
   knowing which harness you're authoring it for.

2. **Persona ↔ model.** "My data-scientist persona uses Sonnet" bakes
   model selection into the persona definition. The same persona on a
   different model is now a different persona, and changing models
   for cost or capability reasons forces a redefinition.

The per-thread ACP harness binding in this fork unbundles axis 1 from
axis 3 at the chat layer: a chat is bound to one harness, and the
harness's models/modes/skills are surfaced as separate selectors. But
it doesn't, on its own, say what a *persona* should be — it just stops
calling the harness one.

## What's a Persona, really?

If you strip away the implementation, a persona is a **bundle of
context that's loaded into a conversation**:

- A system prompt (the "voice" / behavior).
- Optional knowledge or rules ("when working on geospatial data, prefer
  GeoParquet").
- Optional tool wiring (custom MCP servers, allowed shell commands,
  approved file paths).
- Optional metadata about *when* it should activate.

That's it. Everything else — Python class structure, entry-point
registration, mention-name-to-class routing — is plumbing for *how*
the bundle gets delivered, not what the bundle is.

## Skills: the open ecosystem already has the format

[**agentskills.io**](https://agentskills.io/home) is an open standard
that specifies exactly the bundle above. A Skill is a Markdown file
with YAML frontmatter (name, description, when-to-use) plus content
(prompt, tool references, MCP wiring). The standard is multi-vendor
and being adopted across the agent ecosystem — Claude Code, OpenCode,
and others read the same on-disk format from the same standard
locations.

If a persona is a bundle of context, and Skills are an open standard
for bundles of context, then in the simplest case a **persona is a
skill**. Concretely:

```
~/.config/agentskills/data-scientist/SKILL.md
```

```markdown
---
name: data-scientist
description: A senior data scientist. Asks about the analysis goal
  before suggesting code; prefers polars over pandas; calls out
  silent data-quality issues.
when_to_use: When the user is exploring or summarizing tabular data.
---

You are a senior data scientist with ten years of experience...
```

That five-line file is now a persona — usable from any harness that
supports the Skills standard, in any chat surface (Jupyter, terminal
shell, IDE plugin), with no Python class, no entry point, no Jupyter
import.

## Why this matters for Jupyter AI

Three properties fall out of using the open standard rather than
defining a Jupyter-specific surface:

- **Easy to author.** A user who wants a persona writes a
  markdown file. They don't need to know Python, packaging,
  entry-points, or `BasePersona`'s API.
- **Provider-agnostic.** The same persona file works across any
  agent runtime that implements the Skills standard. A persona isn't
  "Claude-flavored" or "OpenCode-flavored" — the same context bundle
  loads into whichever harness the user has bound for that chat.
- **No tool-vendor lock-in.** A persona library a researcher
  builds up across years of Jupyter use isn't trapped inside Jupyter.
  The same files work in their terminal, their editor, their CI
  scripts. Jupyter AI becomes a participating citizen of the broader
  ecosystem rather than a separate one.

These are the reasons the broader community is gravitating toward
open standards in this space — ACP for the wire protocol, Skills for
the context-bundle format, MCP for tool/resource exposure. Each one
trades a small amount of implementation flexibility for a large
amount of portability.

## Where the existing Persona system still fits

The class-based persona surface (`BasePersona` subclasses loaded via
entry points) isn't going away in this framing — it's the *escape
hatch* for personas that genuinely need code:

- A persona that wants to talk to Jupyter Server APIs directly.
- A persona that needs custom Python state across messages within a
  chat (something a stateless skill can't express).
- A persona whose behavior is generated dynamically (e.g., from a
  catalog query).

The proposal is not "delete the Python persona surface." It's
"recognize that the *common* case — most personas, written by most
users — is just a context bundle, and that bundle has a name and a
file format already." The Python surface stays for the cases where
code is genuinely the right answer.

A useful mental ratio: if 90% of users want a persona that's a system
prompt plus some rules, they should be writing a 10-line markdown
file. The remaining 10% who need code can keep using `BasePersona`.

## What the bridge actually does today

This fork's bridge gives you the substrate for the reframe even
without any further upstream change:

- It stops calling the harness a persona. Each chat is bound to a
  harness via the augmented `+ New chat` dialog, and harness
  selection is independent of model and mode selection.
- It surfaces the bound harness's *available skills* as slash-command
  completions in the chat input (read from ACP's
  `AvailableCommandsUpdate` event).
- It forwards `/<skill-name>` invocations through to the harness,
  whose own Skills loader handles the rest.

So if a user has `~/.config/agentskills/data-scientist/SKILL.md`
on disk and they're in a Jupyter AI chat bound to any
Skills-supporting harness, they can already type `/data-scientist`
and the agent loads it. The persona experience works today, with no
Jupyter-specific persona registration. The bridge just stays out of
the way.

## A friendly invitation

This is a sketch of a direction, not a pull request. The Personas
vision in jupyter-ai-persona-manager is a real and good design
contribution. What's changed since it was authored is that the rest
of the open agent ecosystem has converged on standards (ACP, Agent
Skills, MCP) that solve adjacent problems. Aligning with those — for
the *common* case where alignment is cheap — turns the Personas vision
from "the way Jupyter AI does this thing" into "the way Jupyter AI
participates in how the open ecosystem does this thing." That feels
like a worthwhile direction to discuss.

The bridge in this fork is a working artifact arguing the case. It
doesn't need to be merged as-is or even at all to make the point —
the point is the framing, and the framing is the conversation.
