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
  per harness. (Today our wrapper's `get_session_state` is a stub,
  but the contract is in place; see follow-up below.)

## Known gaps and follow-ups

These are the items that did NOT land in the PoC. Each is a small
deliverable on its own and can be tackled independently:

### G1. Toolbar registration of selectors

`@jupyter/chat` exports `IInputToolbarRegistry` as a class and
interface but does not export it as a JupyterFrontEnd token. Without a
token, plugins can't get a reference to call `addItem(...)`. The bridge
exports `ModelSelector`, `ModeSelector`, and `ConfigOptionsSelector`
from its public API; consumers can render them manually, but
auto-attachment to the chat input toolbar requires a small upstream
change to `@jupyter/chat`. The clean upstream PR is one of:

1. Re-export the existing `InputToolbarRegistry` instance via a new
   `IInputToolbarRegistry` token.
2. Construct the registry as a `Token`-provided service so plugins
   can `requires: [IInputToolbarRegistry]` like they already can for
   `IChatCommandRegistry`.

Until then, the selectors are testable in isolation but not visually
present in the chat input.

### G2. Real ACP RPC for set-model / set-mode / set-config-option

`JaiAcpClient` does not yet expose convenience methods for sending
`acp.SetSessionModelRequest`, `acp.SetSessionModeRequest`, and the
`SetSessionConfigOption*Request` family. The bridge harness wrappers
have stub setters with TODO comments referencing these types. The
follow-up is either to add helpers on `JaiAcpClient` (preferred — keeps
the bridge wrappers small) or to do the RPC plumbing inside the bridge
wrapper classes (workable but duplicates logic if multiple harnesses
need it).

### G3. Reading capability state from the live session

`get_session_state()` on the bridge harness wrappers currently
returns an empty capability set. Once the live session response is
exposed via `JaiAcpClient` (or via reading the persona's
`_client_session_future`), populating `available_models`,
`session_modes`, and `config_options` is straightforward.

### G4. Fake-ACP-agent integration test

A protocol-correct fake agent that advertises specific
models/modes/config-options would let us assert end-to-end that the
selectors render the advertised capabilities. Pending G2 + G3.

### G5. Additional harness adapters

Currently registered: Claude Code, OpenCode. The contrib package has
adapters for Codex, Copilot, Gemini, Goose, Kiro, and Mistral Vibe;
each is a few-line addition under `harnesses/`. None block the PoC.
