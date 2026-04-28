# `jupyter-ai-acp-bridge`: A Zed-style ACP client layer for Jupyter AI

**Status:** Draft for review
**Date:** 2026-04-28
**Author:** Carl Boettiger (cboettig)
**Related:** [`jupyterlab/jupyter-ai#1558`](https://github.com/jupyterlab/jupyter-ai/issues/1558)

## 1. Background

Jupyter AI v3 introduces ACP (Agent Client Protocol) support. The current
implementation expresses each ACP harness — Claude Code, Gemini CLI, OpenCode,
Goose, Codex, GitHub Copilot, Kiro, Mistral Vibe — as a `BaseAcpPersona`
subclass registered in the persona registry. Users invoke a harness with an
`@`-mention (e.g. `@claude`, `@gemini`) in chat.

This conflates two orthogonal axes:

1. **Harness selection** — which ACP server runs (a function of
   subscription/billing, capability surface, and user preference).
2. **Model selection** — which LLM the harness talks to (Claude Sonnet vs.
   Opus, GPT-4 vs. GPT-5, …); most harnesses can talk to many models.

The conflation has concrete consequences:

- Multi-harness chats can't share context. Each `BaseAcpPersona` keeps its own
  ACP session and subprocess; `@claude` then `@gemini` in the same chat are two
  isolated conversations rendered in the same transcript.
- The harness's own `@file` and `/`-command syntax is unreachable through the
  Jupyter AI input — `@` is reserved by the persona router.
- Model, effort, and approval-mode switchers — first-class affordances in every
  modern AI IDE — have no natural home in a `@persona`-shaped UI.
- Building a "specialized agent" forces the developer to lock users into a
  single harness, when in practice agent specialization should live above the
  harness layer (AGENTS.md, agent skills, MCP prompts, eventually A2A).

[Zed](https://zed.dev/acp) — co-creator of ACP — solves this with a
**per-thread, single-agent** model. A chat thread is bound to one ACP agent for
its life; selectors for model, session mode (plan / accept-edits / …), and
arbitrary session config options sit in the panel toolbar and hide themselves
when the agent doesn't advertise the corresponding ACP capability. This
proposal ports that model to Jupyter AI as a new, additive extension package:
`jupyter-ai-acp-bridge`.

## 2. Goals and non-goals

### Goals

- A chat thread can be bound to exactly one ACP agent ("harness") for its
  lifetime, fixed at first message.
- The chat panel exposes harness identity, model selector, session-mode
  selector, and session-config-options selector — each driven by ACP
  capabilities the harness advertises, hidden when absent.
- The harness's `available_commands` (slash commands like `/permissions`,
  `/clear`, `/help`) are surfaced in the input via completion and validated
  before send.
- The chat input's `@`-mentions for Jupyter context (notebooks, cells, files)
  resolve client-side into typed ACP `Resource` / `ResourceLink` content
  blocks, mirroring Zed's behavior, so the harness sees structured context, not
  literal `@` text.
- Existing `BasePersona` instances (jupyternaut, custom user personas) keep
  working in any chat. `@<persona-name>` in a harness-bound chat still routes
  to the persona for that one message.
- Global default harness and per-harness default model / mode live in
  jupyter-ai settings; per-thread state stores only the bound harness id (Zed's
  pattern).
- Additive: zero changes to `jupyterlab_chat`; no removal of any existing
  package; existing `acp_personas/*.py` registry entries continue to function
  for users who don't install this extension.

### Non-goals

- Multi-agent orchestration in a single chat. That's A2A's territory and out
  of scope; harness-as-`@persona` is explicitly the pattern we're replacing,
  not generalizing.
- Replacing `jupyter-ai-persona-manager` or `jupyter-ai-router`. They keep
  their current responsibilities; this package layers on top.
- Deleting the `acp_personas/*.py` adapters in `jupyter-ai-acp-client`.
  Deprecation, if any, is a follow-up coordinated with the contrib team.
- Custom-agent registry / extension-provided agents (Zed has these; PoC ships
  one hard-coded harness). This is an obvious follow-up but not v1.
- Authentication UX beyond what `BaseAcpPersona` already provides.

## 3. Architectural overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    jupyterlab_chat (unchanged)                  │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  Chat panel                                             │   │
│   │  ┌──────────────────────────────────────────────────┐   │   │
│   │  │  Harness badge / picker  ←── jupyter-ai-acp-bridge   │
│   │  └──────────────────────────────────────────────────┘   │   │
│   │  ┌──────────────────────────────────────────────────┐   │   │
│   │  │  Message log (existing)                          │   │   │
│   │  └──────────────────────────────────────────────────┘   │   │
│   │  ┌──────────────────────────────────────────────────┐   │   │
│   │  │  Input + selectors (model / mode / config)       │   │   │
│   │  │  ←── jupyter-ai-acp-bridge                       │   │   │
│   │  └──────────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ ACP messages
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│        jupyter-ai-acp-bridge  (NEW — this proposal)             │
│                                                                 │
│   • Per-thread harness binding (chat metadata)                  │
│   • Capability-driven UI: model / mode / config-options         │
│   • @-mention resolution to typed content blocks                │
│   • / -command completion against available_commands            │
│   • REST routes for set_model / set_mode / set_config_option    │
│                                                                 │
│   uses ↓ as a library (not as a registered persona)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│        jupyter-ai-acp-client  (existing, lightly extended)      │
│                                                                 │
│   • BaseAcpPersona — subprocess, ACP session, slash-cmd capture │
│   • acp_personas/*.py — existing @claude / @gemini / … entries  │
│     (untouched; coexist with the bridge)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│   jupyter-ai-router  +  jupyter-ai-persona-manager  (unchanged) │
└─────────────────────────────────────────────────────────────────┘
```

### Key design decisions

| Decision | Choice | Rationale |
|---|---|---|
| Scope | New additive package, not a fork of existing repos. | Matches contrib team's modular philosophy; lowers PR friction; coexists with existing personas. |
| Per-thread vs global harness | Per-thread, with global default in settings. | Matches Zed; matches `acp_session_ids` chat metadata that's already keyed per chat. |
| Mid-thread switching | **Not allowed.** Switching means a new chat. | Matches Zed; makes the per-chat ACP session a stable invariant; eliminates a class of confusing UI states. |
| `@persona` coexistence | Harness gets all unaddressed messages; `@<name>` intercepted only when `<name>` is a registered non-harness `BasePersona`. `@claude` / `@gemini` etc. **not** in registry → fall through to harness verbatim. | Preserves jupyternaut and custom-persona use cases; removes the harness-as-persona conflation cleanly. |
| Selector population | **Pure ACP**, capability-by-trait. Model selector iff agent advertises `available_models`; mode selector iff agent advertises session modes; config-options selector iff agent advertises them. | Mirrors Zed's `Option<dyn AgentModelSelector>` / `Option<dyn AgentSessionModes>` pattern. No per-harness adapter declares model lists. |
| Effort / reasoning level | **Not modeled as a separate concept.** If a harness wants it, it advertises a session config option. | Matches Zed (no `reasoning_effort` for external agents anywhere in `agent_servers` / `agent_ui` / `acp_thread`). |
| `@`-mention resolution | Client-side resolution to typed `acp::ContentBlock::Resource` / `ResourceLink`. Persona-name `@`s intercepted **before** resolution. | Matches Zed (`MessageEditor::build_content_blocks`). The harness sees structured context, not `@` text. |
| `/`-command handling | Validate against `available_commands`; pass verbatim. Refuse to send if unknown. | Matches Zed (`MessageEditor::validate_slash_commands`). |
| Per-thread persistence | Bound harness id only. Model/mode looked up from settings or recovered via ACP session resume. | Matches Zed (`ThreadMetadata.agent_id`); minimizes drift between persisted state and current capabilities. |
| Subprocess sharing | One subprocess per harness, ref-counted, sessions multiplexed inside. | Already how `BaseAcpPersona` works; no change. |

## 4. Component breakdown

### 4.1 Python package `jupyter_ai_acp_bridge/`

```
jupyter_ai_acp_bridge/
├── __init__.py
├── extension.py            # Jupyter Server extension entry point
├── bridge.py               # Per-chat harness-binding manager
├── harness_registry.py     # ID → adapter info
├── harnesses/
│   ├── __init__.py
│   └── claude_code.py      # PoC adapter: executable, env, auth, icon
├── routes.py               # REST endpoints for selectors
├── mention_resolver.py     # Maps Jupyter @-mentions → ACP content blocks
└── tests/
```

**`bridge.py`** owns the per-chat lifecycle. For each chat (keyed by `ychat`
id) it tracks: `harness_id` (None until first message), the underlying
`BaseAcpPersona`-derived client, and current `selected_model_id` /
`selected_mode_id` / `config_option_values`. State machine:

- **draft** — chat exists, no first message yet, no harness bound. Picker
  visible; selectors hidden.
- **bound** — first message sent. `harness_id` written to chat metadata; ACP
  session created; selectors visible (capability-permitting); picker collapses
  to a non-interactive identity badge.

The bridge wraps an existing `BaseAcpPersona` subclass *as a library
consumer* — instantiating it directly with the right executable rather than
relying on the persona registry. Subprocess sharing per-harness already lives
inside `BaseAcpPersona` via class-level `_subprocess_future`; nothing to add.

**`harness_registry.py`** maps each harness id to a small descriptor:

```python
@dataclass
class HarnessAdapter:
    id: str                         # "claude-code"
    display_name: str               # "Claude Code"
    icon: str                       # url or jupyter-asset path
    executable: list[str]           # e.g. ["claude-code-acp"]
    env: dict[str, str] | None
    persona_class: type[BaseAcpPersona]   # the adapter we wrap
```

This is intentionally narrow: no model lists, no effort levels, no mode names.
Everything else is queried from the live ACP session.

**`harnesses/claude_code.py`** is the PoC adapter. It's roughly:

```python
CLAUDE_CODE = HarnessAdapter(
    id="claude-code",
    display_name="Claude Code",
    icon="…",
    executable=ClaudeCodeAcpPersona.executable_spec(),   # delegated; see note
    env=None,
    persona_class=ClaudeCodeAcpPersona,  # imported from acp-client
)
```

Re-using the existing `ClaudeCodeAcpPersona` class as the underlying client
class is the entire point: we don't reimplement subprocess, session, or
slash-command capture. The exact executable invocation is whatever the
existing class already uses; the planning step verifies the precise way to
extract it (a class method, an attribute, or a small refactor of the
constructor).

**`extension.py`** registers the Jupyter Server extension, mounts REST routes,
and registers the harness registry. Settings (default harness id, per-harness
defaults) are read here.

**`routes.py`** exposes:

- `GET  /jupyter-ai-acp-bridge/harnesses` — registry listing for the picker.
- `POST /jupyter-ai-acp-bridge/chats/{chat_id}/bind` — bind a harness to a
  chat (rejected if already bound).
- `GET  /jupyter-ai-acp-bridge/chats/{chat_id}/state` — current harness id,
  selected model id, selected mode id, available models/modes/config options.
- `POST /jupyter-ai-acp-bridge/chats/{chat_id}/model` — set model.
- `POST /jupyter-ai-acp-bridge/chats/{chat_id}/mode`  — set mode.
- `POST /jupyter-ai-acp-bridge/chats/{chat_id}/config-option` — set a config
  option value.
- `GET  /jupyter-ai-acp-bridge/chats/{chat_id}/available-commands` — current
  slash-command list, used by the input completion provider.

**`mention_resolver.py`** holds the policy for converting Jupyter `@`-mentions
to ACP content blocks. Initial mappings:

| `@`-mention | ACP block |
|---|---|
| `@notebook` (active notebook) | `ResourceLink { uri: "file://<path>" }` |
| `@cell` (active cell)         | `Resource { uri: "jupyter-cell://<notebook>/<cell_id>", text: "<source>" }` |
| `@<filepath>`                 | `ResourceLink { uri: "file://<resolved>" }` |
| `@<persona-name>`             | **left as plain text**; not resolved |

The custom URI scheme for cells (`jupyter-cell://…`) is opaque to the harness;
the harness reads `text` for content. (See §7.1 for risk discussion.)

The flow is: the client-side completion provider distinguishes Jupyter
resources (notebooks, cells, files) from registered persona names. Resource
mentions are replaced inline with typed `Resource` / `ResourceLink` content
blocks at send time. Persona mentions are *not* replaced — they remain as
literal `@<persona-name>` text in the message body, where the server-side
routing rule in §5 picks them up.

### 4.2 TypeScript / JupyterLab extension `src/`

```
src/
├── index.ts                      # plugin registration
├── harness-picker.tsx            # draft-state picker at top of panel
├── harness-badge.tsx             # bound-state identity badge
├── selectors/
│   ├── model-selector.tsx
│   ├── mode-selector.tsx
│   └── config-options-selector.tsx
├── slash-completion.ts           # input completion against available_commands
├── mention-completion.ts         # @-mention completion (notebooks, cells, files)
├── api.ts                        # client for the REST routes above
└── __tests__/
```

Selectors hide themselves when the corresponding REST state response shows the
capability is absent (empty `available_models`, no `session_modes`, no
`config_options`). This is the literal Zed pattern, expressed via React
conditional rendering rather than `Option<dyn …>`.

### 4.3 Persistence

**Chat metadata (in `ychat` document):**

- `acp_bridge.harness_id: string | null` — bound harness id; written once on
  first send; treated as immutable thereafter.
- `acp_session_ids: { <persona_id>: <session_id> }` — already exists; the
  bridge re-uses this for the bound-harness session, keyed by a synthetic
  persona id derived from the harness id.

**Settings schema (`jupyter-ai-acp-bridge` settings):**

```json
{
  "default_harness": "claude-code" | null,
  "harnesses": {
    "claude-code": {
      "default_model": "claude-sonnet-4-5" | null,
      "default_mode":  "default" | null
    }
  }
}
```

Per-harness `default_model` / `default_mode` are applied immediately after the
ACP `session/new` response, mirroring Zed's behavior at
`crates/agent_servers/src/acp.rs:1336`.

## 5. Routing rules

Augment the existing persona router with one preflight check:

```
on_message(chat, msg):
    if chat.acp_bridge.harness_id is set:
        name = parse_at_mention(msg)
        if name and name in registered_non_harness_personas:
            dispatch_to_persona(name, msg)        # existing path
        else:
            dispatch_to_bridge(chat, msg)         # new path
    else:
        existing persona-router behavior unchanged
```

The set `registered_non_harness_personas` is the persona-manager registry
minus any `BaseAcpPersona` subclasses (a one-line filter). This is what makes
`@claude` in a harness-bound chat fall through to the harness as literal text
(or, in Claude Code's case, as a no-op since `@claude` doesn't match a file)
rather than route back into the deprecated persona path.

## 6. UI placement

| Element | Location | State |
|---|---|---|
| Harness picker | Top of chat panel | Visible only in draft state |
| Harness identity badge | Top of chat panel | Visible after binding |
| Model selector | Bottom toolbar near input | Visible iff `available_models` populated |
| Mode selector | Bottom toolbar near input | Visible iff `session_modes` populated |
| Config-options selector | Bottom toolbar near input | Visible iff at least one config option advertised |
| Slash-command completion | Inside input, on `/` | Always (when bound) |
| `@`-mention completion | Inside input, on `@` | Always |
| Defaults (default harness, per-harness default model/mode) | JupyterLab Settings Editor | Always |

No changes to `jupyterlab_chat` itself. All UI lives in the bridge's plugin.

## 7. Risks and open questions

### 7.1 ACP content-block mapping for Jupyter resources

ACP's `Resource` / `ResourceLink` blocks expect URIs. Notebooks have file
URIs. **Cells do not have a standardized URI scheme.** Options:

- Custom scheme `jupyter-cell://<notebook-uri>/<cell-id>` carrying the source
  text inline as `Resource.text`. The harness ignores the URI and reads the
  text — which is what we want for v1.
- Skip URI typing entirely and inline cell source as plain `text` content
  blocks with a `<!-- cell: … -->` marker. Loses structure but is unambiguous.

Recommend the first; v1 ships only `@notebook`, `@cell`, `@<filepath>`.

### 7.2 What happens to in-flight `@claude` chats when the bridge is installed

A user with both `jupyter-ai-acp-client` (existing) and the bridge installed
sees `@claude` in the registry **and** Claude Code in the harness picker. By
design these are independent paths:

- `@claude` in any chat → existing `BaseAcpPersona`-style behavior, isolated
  session.
- Claude Code via the picker → bridge-managed binding for that chat.

This is intentional for the PoC. A user can type `@claude foo` in a
bridge-bound Gemini chat and get a one-shot Claude reply through the legacy
path. Documentation flags this as transitional.

### 7.3 Harness adapters that aren't `BaseAcpPersona` subclasses today

Every existing harness in `acp_personas/*.py` is a `BaseAcpPersona` subclass,
so v1 adapters wrap the existing classes directly. If/when the bridge needs
to support a harness that has no contrib-package adapter, we'll need a thin
`BaseAcpPersona` subclass in `harnesses/`. Not a v1 problem.

### 7.4 Per-harness default reset semantics

If the user changes `default_model` for Claude Code in settings, every
**resumed** Claude Code session re-applies the new default after `session/new`
or `session/load`. Zed has the same behavior; it's simple but means the
"persisted-on-disk" model can silently change. Documented, not solved.

### 7.5 Slash-command pass-through edge cases

Some slash commands (Claude Code's `/permissions`) modify session state.
Whether the resulting state change propagates to our mode selector depends on
the harness emitting the right ACP `session/update` notification. Verified
manually against Claude Code in the PoC milestone.

## 8. PoC scope

The first deliverable is a single PR (or PR-set) that ships:

- `jupyter-ai-acp-bridge` package with one harness adapter (Claude Code).
- All UI affordances above.
- Settings schema with defaults.
- Routing-rule augmentation in the metapackage's wiring (or in the bridge,
  via a router hook — TBD during planning, not now).
- Tests: Python unit tests for bridge state machine, registry, mention
  resolver; TS component tests for picker, selectors, slash-command popup;
  one integration test that boots a fake ACP agent and verifies
  capability-driven selector visibility.
- Documentation: a short user-facing page in `docs/source/users/` and a
  developer-facing rationale page that links to issue #1558.

After the PoC is working and review-ready, additional harness adapters
(Gemini CLI, OpenCode, Codex, Copilot, …) are mechanical follow-ups: each
is a few lines in `harnesses/<id>.py` plus an entry in the registry.

## 9. Out of scope / explicit follow-ups

- A2A / multi-agent orchestration (separate proposal).
- Public ACP registry pull (Zed's `AgentRegistryStore` analog).
- Custom-agent definitions in user settings (Zed's `Custom { command, args, … }`
  variant).
- Removing or formally deprecating `acp_personas/*.py`.
- Auth-flow UX improvements beyond what `BaseAcpPersona` provides.
- Mid-thread harness switching (won't fix; matches Zed).

## 10. Success criteria

- A user installs `jupyter-ai-acp-bridge`, opens a new chat, sees a Claude
  Code option in the picker, selects it, sends a message, and receives a
  response.
- The model dropdown shows the live `available_models` list from Claude
  Code's `session/new`. Picking a different model takes effect on the next
  turn.
- The mode dropdown shows Claude Code's session modes (default /
  accept-edits / plan); switching is reflected in subsequent
  permission-request behavior.
- Typing `/help` in the input completes against Claude Code's advertised
  commands and the response is rendered correctly.
- Typing `@notebook.ipynb` in the input attaches the notebook as a
  structured ACP resource; the harness reads it without seeing literal
  `@notebook.ipynb` text.
- Typing `@jupyternaut, summarize this` in a bridge-bound chat (with
  jupyternaut installed) routes that one message to jupyternaut, leaving
  the bridge session untouched.
- Closing and reopening the chat preserves the harness binding; model and
  mode are recovered from settings or session-resume.
- Attempting to bind a different harness to an already-bound chat is
  refused at the API layer with a clear error.
