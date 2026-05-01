# jupyter-ai-acp-bridge — TODO

Live status of the PoC. Each item is a discrete deliverable; none block
"can someone install it and try the picker," which already works as of
2026-04-30 on `acp-bridge-impl`.

## Resume hints

- Worktree: `/home/cboettig/Documents/github/cboettig/jupyter-ai/.worktrees/acp-bridge-impl/`
- Branch: `acp-bridge-impl` (latest at the time of this writing: `15628b6`)
- Activate: `source .venv/bin/activate` (uv-managed venv at the worktree root)
- Test: `pytest jupyter_ai_acp_bridge/tests/` and `jlpm test`
- Build: `jlpm build` (dev) or `jlpm build:prod` (full labextension bundle)
- Run JupyterLab locally: `jupyter lab --no-browser --port=8888 --ServerApp.token=acp-bridge-demo`
- Verify install path from a fresh venv:
  `uv pip install "git+https://github.com/cboettig/jupyter-ai.git@acp-bridge-impl#subdirectory=jupyter-ai-acp-bridge"`

## What works (don't regress)

- HTTP bind end-to-end: click a harness button → POST `/jupyter-ai-acp-bridge/chats/<chat_path>/bind` → 200 with `{harness_id}`. Picker collapses to badge on success.
- Path resolution mirrors `jupyter-ai-acp-client/routes.py`:
  `file_id_manager.get_id(chat_path) → "text:chat:<file_id>" → persona_managers[room_id].ychat`. Don't reinvent.
- Two harnesses registered (Claude Code, OpenCode).
- Slash-command (`/...`) and `@<filename>` completion are wired through `IChatCommandRegistry`.
- Persona is parented to the per-chat `PersonaManager` so `event_loop`, `log`, `fileid_manager` resolve correctly via traitlets.
- Ships a real JupyterLab labextension bundle (`build:prod` produces it; shared-data publishes it).

## P0 — fix the broken state before claiming done

- [x] **Fix unit tests broken by the `integration`-kwarg → settings rewire.** Resolved 2026-04-30: actual count was 10 (not 3 — the TODO undercounted). All `_BridgeBaseHandler` subclasses route bridge lookup through `self.integration.resolve(chat_path)`, so every test class that hits one of those endpoints needs a fake integration installed in `app.settings["jupyter-ai"]["acp-bridge-integration"]`. Added a module-level `_IdentityIntegration` helper that maps `chat_path -> chat_path` for tests that pre-bind bridges by chat_id. `BindHandlerTest`/`BindHandlerIntegrationTest` use a custom fake whose `bind_chat()` calls through to `bridge.bind()` directly. Also fixed `test_bind_chat_suppresses_default_persona` in `test_router_integration.py`, which called `bind_chat` directly without a `file_id_manager`. 62/62 tests pass.

## P1 — UX redesign (Carl explicitly flagged this as terrible)

- [x] **Move harness selection out of the chat input toolbar entirely; bind at chat-creation time.** Resolved 2026-04-30 (superseded the earlier in-chat dropdown). Per Zed's UX, the user should pick the agent BEFORE the chat exists, not after — re-binding an existing chat isn't supported anyway. Now: each registered harness gets its own JupyterLab launcher card under "ACP agents" (`src/launcher.ts`); clicking runs `jupyterlab-chat:createAndOpen` then calls the bind endpoint with retry/backoff. In-chat toolbar shows the read-only `HarnessBadge` for bound chats and an italic hint pointing at the launcher for unbound ones. The `HarnessPicker` dropdown component still exists and is exported (useful primitive) but is no longer rendered.
- [x] **Persona-loop bug: agent stops replying after a couple of turns.** Resolved 2026-04-30. `_make_msg_handler` was dispatching every chat message in the room — including the bound persona's own replies — back to the persona as if they were user prompts. After ~3 turns the conversation accumulated empty/duplicate content blocks, and `claude-agent-acp` would forward a malformed prompt to Anthropic, getting back `messages.N.content.0.text: cache_control cannot be set for empty text blocks`. Fix: mirror `PersonaManager.on_chat_message` and skip messages whose sender is a persona (`is_persona(sender)`) or `SYSTEM_USERNAME`. Harness-agnostic, also unblocks OpenCode.
- [x] **Restored bindings (`_on_chat_init`) were missing `parent=PersonaManager`.** Resolved 2026-04-30. Reopening a chat with `acp_bridge` metadata called `bridge.bind(adapter)` without a parent, so the persona's `event_loop`/`log`/`fileid_manager` couldn't resolve via traitlets. Mirrors `bind_chat()` now. The launcher flow exercises this on every server restart.
- [x] **Investigate why the picker only renders when the user types `@`.** Resolved 2026-04-30 — was a render-timing artifact, not toolbar gating. `@jupyter/chat`'s input-toolbar always renders all registered items (`chat-input.js` `INPUT_TOOLBAR_CLASS` `Box` is unconditional); but `HarnessHeader` returned `null` while the initial `GET /state` fetch was in flight. Typing `@` triggered a chat-input re-render that coincided with the fetch resolving, making `@` look causal. (Moot now that the in-chat picker is gone, but the eager-render fix is still in place for the badge/hint.)
- (Toolbar-factory conflict with `acp-client` moved to P3; becomes load-bearing only once we add multiple toolbar items in Step 2.)

## P2 — Match Zed's capability-selector UX (model / mode / config-options)

Reference: Zed's `crates/agent_servers/src/acp.rs` (the generic ACP integration — no Claude/OpenCode special-cases) and `crates/agent_ui/src/conversation_view/thread_view.rs:3270` (input-toolbar bottom-row layout).

Confirmed from the ACP schema:
- **Models** live in `NewSessionResponse.models: SessionModelState`. Set once at session creation; **no `CurrentModelUpdate` event exists** (verified — schema only has `SessionInfoUpdate` / `UsageUpdate` / `CurrentModeUpdate` / `AvailableCommandsUpdate` / `ToolCallUpdate` / `ConfigOptionUpdate`). Changed via `connection.set_session_model(model_id, session_id)`.
- **Modes** live in `NewSessionResponse.modes: SessionModeState`. Updated dynamically via `CurrentModeUpdate`. Changed via `set_session_mode`.
- **Config options** live in `NewSessionResponse.config_options: list[Boolean | Select]`. Updated via `ConfigOptionUpdate`. Changed via `set_config_option`.
- **Mutually exclusive in the UI**: when `config_options` is present, the model+mode selectors are hidden (mirroring Zed's `config_state()` which returns either modes/models or config_options, never both).
- **Effort levels are NOT in ACP** — Zed has them as a hardcoded property of certain Claude model IDs (`model.supported_effort_levels()` in the `language_model` crate). Out of scope for this PoC.

- [x] **Backend: real ACP RPC for set-model / set-mode / set-config-option.** Done 2026-04-30 in `_capabilities.AcpBridgeCapabilityMixin`. Goes through `connection.set_session_model(model_id, session_id)` etc. — the ACP client connection already exposes these directly, no raw RPC plumbing needed. Selected model/mode tracked on the persona instance to survive `set_session_*` round-trips (no SessionUpdate event for model changes).

- [x] **Step 1 — Diagnostic.** Done 2026-05-01. claude-agent-acp populates all three of `response.models`, `response.modes`, and `response.config_options` (the latter mirrors the first two with `category: 'model'` / `'mode'`). OpenCode populates models + modes. Three runtime bugs exposed by the diagnostic and fixed: (a) wrong field names on `SessionConfigOption*` (`current_value` not `value`, choice `value` not `id`); (b) `_acp_slash_commands` returned Pydantic objects, not JSON-serializable dicts (now flattened via `model_dump`); (c) observer-ordering: our `_on_chat_init` ran before pm-manager's, so `persona_managers[room_id]` was always empty at our observer time → bind deferred to next event-loop tick.

- [x] **Step 2 — Zed-style row of capability selectors.** Done 2026-05-01. `HarnessHeader` now renders badge → ModelSelector → ModeSelector → ConfigOptionsSelector inline. Each child self-fetches state and hides when its capability is absent (Claude Code: badge + 3-model select + 5-mode select; OpenCode: badge + its model list + plan/build). `ConfigOptionsSelector` filters out entries with `category` ∈ {`'model'`, `'mode'`} since those duplicate the dedicated fields, and renders Boolean / Select / free-text correctly for anything else (mirrors Zed's `config_state()` mutual exclusion).

- [ ] **Step 3 — Reactive updates from `CurrentModeUpdate` / `ConfigOptionUpdate` SessionUpdate events.** Currently each child component fetches `/state` once on mount; if the agent emits a mode-change update mid-session (e.g., the user runs the harness's `/mode plan` slash command), our toolbar lags until the chat is reopened. Bridge-side: subscribe to session updates in the persona's `session_update` handler, mutate the tracked `_acp_bridge_selected_*` attrs. Frontend-side: simplest is poll `/state` every ~5s when chat focused; upgrade to push (websocket / SSE) only if perceptibly laggy.

- [ ] **Step 5 (cleanup) — Remove the once-per-persona diagnostic logging in `_capabilities.py`.** Gated to fire exactly once per persona instance, so harmless, but no longer load-bearing now Steps 1+2 are done. Drop in the same commit as Step 3 lands.

## P3 — Deferred until after the model/mode/config selectors land

- [ ] **Step 4 — Per-chat agent identity selector at the top of the chat panel.** Zed shows `Claude Agent ▾` at the top of the input area; clicking opens an agent picker + the ACP Registry (Zed's marketplace of installable agents). Deferred per Carl 2026-05-01: the augmented `+ New chat` dialog already covers picking an agent at chat creation, and the per-chat picker mostly matters once we have a registry of installable agents to surface (which is itself out of scope for the PoC). Revisit if/when ACP Registry questions land.

- [ ] **Effort selector.** Pure Zed-side concept (model registry mapping certain Claude IDs to effort levels), not in the ACP wire. Skip unless user demand surfaces.

- [ ] **ACP Registry / "Add More Agents" flow.** Zed has a marketplace of installable ACP servers (Agoragentic, Amp, Auggie CLI, etc., per Carl's screenshot 2). Way out of scope for the PoC; needs its own design.

- [ ] **Resolve the toolbar-factory conflict with `acp-client`.** Both packages provide `IInputToolbarRegistryFactory`; only one wins in JupyterLab DI. Becomes more pressing once we add multiple toolbar items in Step 2. Cleanest fix is upstream in `@jupyter/chat` (composable registry).

## P3 — defer until after the issue-thread discussion

- [ ] **Fake-ACP-agent integration test.** Spawns a stdio JSON-RPC server that advertises specific models/modes; verifies the bridge surfaces them. Pending P2 (no point until real RPC is in place).
- [ ] **More harness adapters.** Codex, Copilot, Gemini-CLI, Goose, Kiro, Mistral Vibe each exist as `BaseAcpPersona` subclasses in `jupyter_ai_acp_client.acp_personas.*`; adding each is a near-verbatim mirror of `harnesses/claude_code.py`. Skip until UX is fixed and the picker can comfortably show 8+ entries.
- [ ] **Mention resolution at send time.** The `resolve_mentions` function exists in `jupyter_ai_acp_bridge/mention_resolver.py` and is unit-tested, but isn't wired into the actual send flow yet. Currently the harness sees raw `@filename` text and parses it itself (which Claude Code does natively). Wiring the resolver to translate at send time would emit typed `Resource`/`ResourceLink` content blocks, matching the design spec.
- [ ] **Subprocess shutdown on kernel/server stop.** Bridges hold onto `BaseAcpPersona` instances which spawn `claude-agent-acp` subprocesses; nothing cleans them up. Probably a `disconnect_chat`/`stop_extension` hook.

## Deferred (require upstream changes; documented in the issue thread)

- **`@jupyter/chat`: expose `IInputToolbarRegistry` as a token directly** (currently only `IInputToolbarRegistryFactory`, which forces the factory-replacement pattern).
- **`@jupyter/chat`: composable input-toolbar registry** so multiple plugins can each add items without conflicting.
- **`jupyter-ai-acp-client`: `JaiAcpClient` convenience helpers for `set_session_model` / `set_session_mode` / `set_session_config_option`** — would shrink each adapter wrapper to nothing.

## Engineering-style reminders for resumption

- When a bug recurs after one or two fix attempts, **stop and find the canonical reference implementation** in a sibling package. Mirror it verbatim. Don't stack speculative fallbacks. (Carl flagged this explicitly during the chat-id resolution thrash on 2026-04-30; the eventual fix was three lines copied from `jupyter-ai-acp-client/routes.py`.)
- The PoC's purpose is the **rhetorical anchor for issue #1558**, not production. Don't propose a PR against upstream; people install from the branch, try it, comment on the issue.
- Don't add tests for behavior that isn't there yet — keep the test suite honest.
