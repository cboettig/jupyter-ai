# jupyter-ai-acp-bridge — TODO

Live status of the PoC. The PoC is **functional end-to-end** as of
2026-05-01: install from the branch, click `+ New chat`, pick an
agent, send messages, use model/mode dropdowns, type slash commands.
Everything below is polish / out-of-scope work, not blockers.

> Architectural overview for developers:
> [`docs/source/developers/acp-bridge-rationale.md`](../docs/source/developers/acp-bridge-rationale.md).
> Install + run for users / colleagues:
> [`README.md`](README.md).

## Resume hints

- Worktree: `/home/cboettig/Documents/github/cboettig/jupyter-ai/.worktrees/acp-bridge-impl/`
- Branch: `acp-bridge-impl` (origin auto-updated)
- Activate: `source .venv/bin/activate` (uv-managed venv at the worktree root)
- Test: `pytest jupyter_ai_acp_bridge/tests/` (62 passing) and `jlpm test` (11 passing)
- Build: `jlpm build` (dev) or `jlpm build:prod` (full labextension bundle)
- Sync into the live `share/jupyter/labextensions/...` dir after `jlpm build`
  (the install isn't editable — the build only updates the source tree's
  `jupyter_ai_acp_bridge/labextension/`):
  ```bash
  SHARE=$(pwd)/.venv/share/jupyter/labextensions/@jupyter-ai/acp-bridge
  SRC=$(pwd)/jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/labextension
  rm -rf "$SHARE/static" && cp -r "$SRC/static" "$SHARE/static" && cp "$SRC/package.json" "$SHARE/package.json"
  ```
- Run JupyterLab: `jupyter lab --no-browser --port=8888 --ServerApp.token=acp-bridge-demo --ServerApp.disable_check_xsrf=True`
- Verify install path from a fresh venv:
  `uv pip install "git+https://github.com/cboettig/jupyter-ai.git@acp-bridge-impl#subdirectory=jupyter-ai-acp-bridge"`

## What's working end-to-end

- **Augmented chat creation.** `+ New chat` (sidebar, launcher, command
  palette) shows a single dialog with name + agent fields. After OK,
  the chat is created and bound to the chosen harness via REST. Two
  registered harnesses: Claude Code, OpenCode.
- **Bind restoration on reopen.** Opening an existing bound `.chat`
  file rebinds via `acp_bridge` metadata. Survives the chat
  extension's "divergent history → clear YDoc" recovery path via a
  Y-Map metadata observer that retries restore when metadata syncs in.
- **In-toolbar capability selectors** rendered Zed-style: model →
  mode → config-options → harness label. Each child self-fetches
  state and hides on empty. ConfigOptions filters out
  `category=model`/`category=mode` to avoid duplicating the dedicated
  pickers (`claude-agent-acp` advertises both shapes).
- **Real ACP RPC for setters.** `set_session_model`,
  `set_session_mode`, `set_session_config_option` go through the ACP
  client connection's built-in helpers in
  `_capabilities.AcpBridgeCapabilityMixin`. User-driven dropdown
  changes flip agent state.
- **Slash command forwarding.** `/<skill>` typed in the input is
  forwarded to the bound persona via a wildcard `slash_cmd_observer`
  registration; `/<cmd>` is reconstructed before dispatch so
  `claude-agent-acp`'s slash-skill loader sees the leading slash.
  Filtered to commands the bound persona advertises so `/refresh-personas`
  and other extension-owned commands aren't double-handled.
- **Persona suppression.** Legacy `@`-mention ACP personas from
  `jupyter-ai-acp-client` are suppressed in three places: `pm.personas`
  (dispatch), `pm.ychat._yusers` (mention completion), and
  `PersonaManager._ep_persona_classes` (class-level cache so future
  PMs don't even instantiate them).
- **Persona-loop guard.** Bridge dispatch skips messages whose
  `sender` is a persona or the SYSTEM_USERNAME, mirroring upstream
  `PersonaManager.on_chat_message` — without this the bound persona
  would re-receive its own replies and corrupt the conversation.

## In flight (P2 Step 3)

- [ ] **Reactive `CurrentModeUpdate` / `ConfigOptionUpdate`.** When
  the agent flips mode/config internally (e.g. via its own slash
  command), our cached state lags until the next `/state` request.
  The dropdowns work for *user-driven* changes; only agent-initiated
  changes drift. Bridge-side: hook the persona's `session_update`
  handler, mutate `_acp_bridge_selected_*` instance attrs.
  Frontend-side: simplest is poll `/state` every ~5s while focused;
  upgrade to push (websocket / SSE) only if perceptibly laggy.

## Deferred / out of scope

- [ ] **Image paste (`Ctrl+V`).** Zed-style direct paste into the
  chat input — lives in `@jupyter/chat`'s editor, not here. Either
  upstream a paste handler or hook into the chat-input's paste event
  from a side plugin.
- [ ] **Toolbar-factory conflict with `jupyter-ai-acp-client`.** Both
  packages provide `IInputToolbarRegistryFactory`; only one wins in
  JupyterLab DI. Cleanest fix is upstream in `@jupyter/chat` —
  either expose `IInputToolbarRegistry` as a JupyterFrontEnd token,
  or make the registry composable across plugins.
- [ ] **Per-chat agent identity selector + ACP Registry.** Zed shows
  `Claude Agent ▾` at the top of the chat panel; clicking opens an
  agent picker plus a marketplace of installable ACP servers ("Add
  More Agents"). Deferred — the augmented `+ New chat` dialog already
  covers picking an agent at chat creation, and the registry piece
  is its own design problem.
- [ ] **Effort selector.** Pure Zed-side concept (their
  `language_model` crate maps certain Claude model IDs to effort
  levels), not in the ACP wire. Skip unless user demand surfaces.
- [ ] **More harness adapters.** Codex, Copilot, Gemini-CLI, Goose,
  Kiro, Mistral Vibe each exist as `BaseAcpPersona` subclasses in
  `jupyter_ai_acp_client.acp_personas.*`; adding each is a
  near-verbatim mirror of `harnesses/claude_code.py`. Skip until the
  picker comfortably handles 8+ entries.
- [ ] **Mention resolution at send time.** `mention_resolver.py`
  exists and is unit-tested but isn't wired into the send flow.
  Currently the harness sees raw `@filename` text and parses it
  itself (which Claude Code does natively). Wiring the resolver to
  translate at send time would emit typed `Resource`/`ResourceLink`
  content blocks per the design spec.
- [ ] **Subprocess shutdown on chat / kernel / server stop.** Bridges
  hold onto `BaseAcpPersona` instances which spawn `claude-agent-acp`
  subprocesses; nothing cleans them up. Probably a `disconnect_chat`
  / `stop_extension` hook.
- [ ] **Fake-ACP-agent integration test.** A protocol-correct fake
  agent that advertises specific models/modes/config-options would
  let us assert end-to-end that the selectors render the advertised
  capabilities. Worthwhile for CI; not needed to demo the PoC.

## Upstream paper-cuts (worth filing)

- **`@jupyter/chat`: expose `IInputToolbarRegistry` as a token** —
  currently only `IInputToolbarRegistryFactory` is exposed, which
  forces the factory-replacement pattern. A token would let multiple
  plugins each `addItem(...)` without conflicting.
- **`@jupyter/chat`: composable input-toolbar registry** so
  multiple plugins can each contribute toolbar items without
  factory-collisions.
- **`@jupyter/chat`: paste-into-input** — see "Image paste" above.
- **`jupyter-ai-acp-client`: `JaiAcpClient` convenience helpers** for
  `set_session_model` / `set_session_mode` / `set_session_config_option`
  (these are present on the underlying `ClientSideConnection` but not
  re-exposed on the friendlier `JaiAcpClient` wrapper). Would shrink
  each adapter wrapper to nothing.

## Engineering reminders for resumption

- When a bug recurs after one or two fix attempts, **stop and find
  the canonical reference implementation** in a sibling package or in
  Zed's source. Mirror it verbatim. Don't stack speculative
  fallbacks. (Carl flagged this on 2026-04-30 during the chat-id
  resolution thrash; the fix was three lines copied from
  `jupyter-ai-acp-client/routes.py`. Same lesson on 2026-05-01: the
  slash-command silent-drop bug was solved by reading the router
  source, not guessing.)
- The PoC's purpose is the **rhetorical anchor for issue #1558**, not
  production. Don't propose a PR against upstream; people install
  from the branch, try it, comment on the issue.
- Don't add tests for behavior that isn't there yet — keep the test
  suite honest.
