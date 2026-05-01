# ACP harness selector (preview)

The `jupyter-ai-acp-bridge` package adds Zed-style per-thread ACP harness
binding to Jupyter AI as a preview. Each new chat is bound to one ACP
harness for its lifetime; switching harness means starting a new chat.

This is a proof-of-concept demonstration of the design proposed in
[issue #1558](https://github.com/jupyterlab/jupyter-ai/issues/1558). It is
additive — installing it does not change the behavior of any existing
Jupyter AI personas (`jupyternaut`, your custom personas, etc., continue to
work as before). Note that when the bridge is installed it does suppress
the legacy `@`-mention ACP personas (`@Claude`, `@OpenCode`, etc.) shipped
by `jupyter-ai-acp-client`, since the bridge supersedes them — they go
through the same `claude-agent-acp` / `opencode` subprocess either way, so
having both as separate UI surfaces was confusing.

## Install

The bridge is **not on PyPI** — it lives on the `acp-bridge-impl` branch of
the [cboettig/jupyter-ai](https://github.com/cboettig/jupyter-ai) fork as a
PoC. Install directly from the branch:

```
pip install \
  "git+https://github.com/cboettig/jupyter-ai.git@acp-bridge-impl#subdirectory=jupyter-ai-acp-bridge"
```

This pulls in `jupyter-ai-acp-client`, `jupyter-ai-router`,
`jupyter-ai-persona-manager`, and `jupyterlab-chat` from PyPI as transitive
dependencies, and builds the JupyterLab extension bundle at install time
(Node.js needs to be available).

Then install at least one ACP harness binary on PATH:

- Claude Code requires `claude-agent-acp` (see Claude Code docs).
- OpenCode requires `opencode` (see [opencode.ai](https://opencode.ai)).

See the package's
[README](https://github.com/cboettig/jupyter-ai/blob/acp-bridge-impl/jupyter-ai-acp-bridge/README.md)
for the full install/verify/run flow.

## Use

1. Click **+ New chat** in the chat sidebar (or **Chat** in the launcher,
   or use the command palette).
2. The bridge augments the standard "Create a new chat" dialog with an
   **Agent** selector — pick a name and a harness (Claude Code, OpenCode,
   …) in the same step and hit **Create**.
3. The chat opens already bound to the chosen harness; type and send.
4. To use a different harness, start a new chat. Mid-thread switching
   isn't supported — same constraint Zed has, since the agent's session
   state is harness-specific.

For chats bound to a harness that advertises a model list (Claude Code
exposes Default / Sonnet / Haiku, for example), a model `<select>` appears
next to the harness badge in the chat input toolbar.

## Limitations of the preview

- **Mode and config-option selectors aren't rendered yet.** Only the
  model selector is mounted. Mode (plan / build, accept-edits, bypass…)
  and config-options exist as backend state and as standalone React
  components, but the toolbar layout work to render them as separate
  Zed-style toolbar items is still in progress (P2 Step 2 in the repo
  TODO).
- **No live updates for mode/config changes.** If the agent emits a
  `CurrentModeUpdate` or `ConfigOptionUpdate` during a session (e.g., a
  slash command toggles plan/build), the bridge's tracked state catches
  up only on the next `/state` poll. Reactive push (or simple polling)
  is P2 Step 3.
- **No effort selector.** Effort levels aren't carried by the ACP
  protocol — Zed has them as a hardcoded property of certain Claude
  model IDs. Out of scope for this PoC.
- **No mid-thread harness switching.** Intentional, matches Zed.
- **No per-chat agent identity selector at the top of the chat panel,
  no ACP Registry / "Add More Agents" flow.** Both deferred until the
  rest of the toolbar selectors land — see the repo TODO for the plan.

See `docs/superpowers/specs/2026-04-28-acp-bridge-design.md` for the full
design rationale and the developer page below for an architectural map.
