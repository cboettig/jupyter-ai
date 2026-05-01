# ACP bridge: rationale and architectural map

This document accompanies the PoC at
[`jupyter-ai-acp-bridge`](../../../jupyter-ai-acp-bridge/) and the
design spec at
`docs/superpowers/specs/2026-04-28-acp-bridge-design.md`.

## Why a separate package?

The bridge demonstrates the design proposed in
[issue #1558](https://github.com/jupyterlab/jupyter-ai/issues/1558):
ACP harnesses should not be exposed as `@`-mentionable personas, because
that conflates harness selection with model selection and breaks
per-thread context isolation. Instead, a chat thread is bound to one
harness for its life, with capability-driven toolbar selectors for
model, session mode, and arbitrary session config options — all sourced
from what the harness advertises via ACP, not from per-harness
hard-coding.

The package is purely additive. Existing `acp_personas/*` registry
entries (`@claude`, `@gemini`, etc.) continue to work; jupyternaut and
custom `BasePersona` extensions are untouched. A user installing the
bridge sees a new "harness picker" affordance for new chats; everything
else is unchanged.

## Architecture map

The Python side has six small modules under
`jupyter_ai_acp_bridge/`:

- `adapter.py` — `HarnessAdapter` dataclass, the static metadata for
  one harness.
- `registry.py` — `HarnessRegistry`, the in-memory map.
- `bridge.py` — `ChatBridge`, the per-chat state machine
  (draft → bound, immutable after) plus capability ops.
- `manager.py` — `BridgeManager`, the per-room map of `ChatBridge`s.
- `mention_resolver.py` — pure function that translates
  user-typed input strings to ACP `ContentBlock` dicts.
- `handlers.py` — Tornado handlers for the seven REST routes.
- `router_integration.py` — observer-pattern hook into
  `jupyter-ai-router` plus persona-manager coordination.
- `harnesses/claude_code.py`, `harnesses/opencode.py` — adapter
  modules per harness, each subclassing the existing `BaseAcpPersona`
  subclass from `jupyter_ai_acp_client`.

The TypeScript side has parallel layers:

- `src/types.ts` — TypeScript types matching the REST payloads.
- `src/api.ts` — `ServerConnection`-based REST client.
- `src/components/HarnessPicker.tsx` — draft-state picker.
- `src/components/HarnessBadge.tsx` — bound-state identity badge.
- `src/components/HarnessHeader.tsx` — composer that switches between
  picker and badge based on bridge state.
- `src/components/ModelSelector.tsx`, `ModeSelector.tsx`,
  `ConfigOptionsSelector.tsx` — capability selectors that hide when
  the bound harness doesn't advertise the corresponding capability.
- `src/providers/BridgeSlashCommandProvider.ts` — `/`-command
  completion against the harness's advertised commands.
- `src/providers/BridgeMentionProvider.ts` — `@<filename>`
  completion against workspace files.

The package's default export is an array of three plugins: a top-level
"loaded" notifier and the two completion providers.

## Reference: Zed's ACP integration

The design closely mirrors Zed's `crates/acp_thread` and
`crates/agent_servers` (see
[zed-industries/zed](https://github.com/zed-industries/zed)). Specifically:

- Per-thread agent binding stored as a single `agent_id` on the
  thread record (Zed: `ThreadMetadata`, here: `ychat` metadata under
  `acp_bridge`).
- Capability-by-trait pattern: each optional capability (model
  selector, session modes, config options) is an `Option<dyn …>` in
  Zed; here it's an optional dict-key in `bridge.get_state()`. UI
  hides when the capability is absent in both implementations.
- Models come straight from ACP `available_models` — never hard-coded
  per harness. `get_session_state()` reads them from the cached
  `NewSessionResponse.models`, mirroring Zed's `config_state()` in
  `crates/agent_servers/src/acp.rs`.

## Status snapshot (as of 2026-05-01)

What works end-to-end:

- **Per-chat binding via the augmented "Create a new chat" dialog.** The
  bridge replaces `jupyterlab-chat:create` with a wrapper that asks for
  both name and harness in one dialog, then delegates to the original
  command and binds via the bridge `/bind` REST endpoint with retry. All
  chat-creation entry points (sidebar `+`, "Chat" launcher card,
  command-palette "Create a new chat") flow through it.
- **Read-only badge in the chat input toolbar** for bound chats; an
  italic hint pointing back at the launcher for unbound chats.
- **Real ACP RPC for setters.** `set_session_model` / `set_session_mode`
  / `set_session_config_option` go through the ACP client connection's
  built-in `set_session_model(model_id, session_id)` etc. — no raw
  JSON-RPC plumbing needed in the wrappers. Lives in
  `_capabilities.AcpBridgeCapabilityMixin`.
- **Live capability state** read from `NewSessionResponse.models` /
  `.modes` / `.config_options`. Surfaces `available_models`,
  `session_modes`, `config_options` in `/state`.
- **Model selector** rendered inline next to the badge for harnesses
  that advertise a model list (Claude Code: Default / Sonnet / Haiku).

What's still in flight (mapped to TODO.md P2 step numbers):

### G1. Zed-style toolbar layout (P2 Step 2)

Currently the badge + `<select>` are jammed inline in one toolbar
item. Zed renders them as separate items in a horizontal row above
the send button: badge, then mode selector, then model selector — and
when `config_options` is present (which claude-agent-acp does, with
`category: 'model'` / `'mode'` mirroring the dedicated fields), the
mode + model selectors are *replaced* by config-options renderers.
The `ModeSelector` and `ConfigOptionsSelector` React components
already exist; this is the toolbar wrapper + index.ts registration
work, not new components. Loosely blocked on G3 (factory conflict)
becoming load-bearing once we have multiple toolbar items.

### G2. Reactive `CurrentModeUpdate` / `ConfigOptionUpdate` handling (P2 Step 3)

The agent can change mode or config internally (slash command toggles
plan/build, etc.); we need the UI to reflect that. Bridge-side: hook
the persona's `session_update` handler. Frontend-side: cheap is poll
`/state` every 5s when the chat is focused; push (websocket / SSE) is
a follow-up.

### G3. Toolbar-factory conflict with `jupyter-ai-acp-client`

Both packages provide `IInputToolbarRegistryFactory`; only one wins
in JupyterLab DI. Currently a paper cut (the bridge's read-only badge
loses gracefully if outranked); becomes load-bearing once we add
multiple toolbar items in G1. Cleanest fix is upstream in
`@jupyter/chat` — either expose `IInputToolbarRegistry` as a token
directly, or make the registry composable across plugins.

### G4. Fake-ACP-agent integration test

A protocol-correct fake agent that advertises specific
models/modes/config-options would let us assert end-to-end that the
selectors render the advertised capabilities. Worthwhile once G1 is
in.

### G5. Additional harness adapters

Currently registered: Claude Code, OpenCode. The contrib package has
adapters for Codex, Copilot, Gemini, Goose, Kiro, and Mistral Vibe;
each is a few-line addition under `harnesses/`. None block the PoC.

### G6. Per-chat agent identity selector + ACP Registry (P3, deferred)

Zed shows `Claude Agent ▾` at the top-left of the chat panel; click
opens an agent picker plus a marketplace of installable ACP servers
("Add More Agents"). Deferred — the augmented `+ New chat` dialog
already covers picking an agent at chat creation, and the registry
piece is its own design problem.
