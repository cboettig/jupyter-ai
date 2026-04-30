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

- [x] **Replace inline-buttons-in-toolbar layout with a single dropdown button**, Zed-style. Done 2026-04-30. `HarnessPicker` is now a single `Pick agent ▾` button that opens a popover menu of harnesses; pure React (no Lumino) with `useRef` + document `mousedown` for click-outside dismiss. CSS lives in `style/index.css` (referenced from `package.json`'s `style` field), uses JupyterLab `--jp-*` theme variables. Bound state still shows the read-only `HarnessBadge` (no chevron — rebinding isn't supported by the API; revisit if/when it is).
- [x] **Investigate why the picker only renders when the user types `@`.** Resolved 2026-04-30 — was a render-timing artifact, not toolbar gating. `@jupyter/chat`'s input-toolbar always renders all registered items (`chat-input.js` `INPUT_TOOLBAR_CLASS` `Box` is unconditional); but `HarnessHeader` returned `null` while the initial `GET /state` fetch was in flight. Typing `@` triggered a chat-input re-render that coincided with the fetch resolving, making `@` look causal. Fix: render a disabled `Pick agent ▾` placeholder button while `state === null`, so the slot is never empty.
- [ ] **Resolve the toolbar-factory conflict with `acp-client`.** Both packages provide `IInputToolbarRegistryFactory`; only one wins in JupyterLab DI. Either compose (provide a wrapping factory that reads from a known token) or document explicitly which-wins-when. This is also a small upstream paper-cut worth noting in the issue thread.

## P2 — make the capability dropdowns actually functional

- [ ] **Implement real ACP RPC for set-model / set-mode / set-config-option.**
  - `JaiAcpClient` does NOT expose convenience helpers. Have to construct ACP requests directly using types from the `acp` Python package.
  - Stubs are in `jupyter_ai_acp_bridge/harnesses/claude_code.py` and `opencode.py`, methods `set_session_model`, `set_session_mode`, `set_session_config_option`. Each has a TODO comment naming the request type.
  - Pattern likely:
    ```python
    from acp import SetSessionModelRequest
    client = await self.get_client()
    session_id = await self.get_session_id()
    await client.get_connection().send_request(
        SetSessionModelRequest(session_id=session_id, model_id=model_id)
    )
    ```
    Verify against the running ACP protocol — types and method may need adjustment.
- [ ] **Read live capability state from the ACP session.**
  - `get_session_state()` currently returns empty arrays for `available_models`, `session_modes`, `config_options`.
  - Pull from `await self.get_session_response()` (returns `NewSessionResponse | LoadSessionResponse` from `BaseAcpPersona._client_session_future`). Inspect the response object's attributes; ACP defines `SessionModelState`, `SessionModeState`, `ConfigOptionUpdate` etc. as schema types.
  - Once populated, the `ModelSelector`/`ModeSelector`/`ConfigOptionsSelector` React components will start rendering — they hide when the array is empty.

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
