# ACP harness selector (preview)

The `jupyter-ai-acp-bridge` package adds Zed-style per-chat ACP harness
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
4. To use a different harness, start a new chat. Mid-chat switching
   isn't supported — same constraint Zed has, since the agent's session
   state is harness-specific.

Inside a bound chat the chat-input toolbar shows a Zed-style row of
selectors driven entirely by what the harness advertises:

- **Model** picker — Claude Code exposes `Default (recommended)` /
  `Sonnet` / `Haiku`; OpenCode exposes its own list of configured
  models.
- **Mode** picker — Claude Code: `Default` / `Accept Edits` /
  `Plan Mode` / `Don't Ask` / `Bypass Permissions`. OpenCode: `plan`
  / `build`.
- Any other agent-advertised **config options** (Boolean toggles,
  Select dropdowns, free-text), de-duplicated against the model/mode
  pickers when the agent advertises them through both surfaces.
- A read-only **harness label** at the end of the row identifying the
  bound agent.

Each selector renders only when the harness actually advertises that
capability, so a harness that only exposes models simply hides the
mode picker. Slash commands typed in the chat input (e.g. `/<skill-name>`)
auto-complete from the harness's advertised commands and forward to
the agent for evaluation — agents that load skills at the start of a
prompt (like `claude-agent-acp`) work end-to-end.

## Limitations of the preview

- **Agent-initiated mode changes lag the UI.** The user-facing dropdown
  works for changing model/mode; what's not yet wired is the reverse
  direction — if the agent flips mode internally (via its own slash
  command, say) the dropdown reflects the change only on the next
  reload. Reactive polling / push is P2 Step 3 in the repo TODO.
- **No image paste (`Ctrl+V`) into the chat input.** Zed lets you paste
  an image directly; here you have to use the attach button. Lives in
  `@jupyter/chat`'s editor, not in the bridge.
- **No effort selector.** Effort levels aren't carried by the ACP
  protocol — Zed has them as a hardcoded property of certain Claude
  model IDs. Out of scope for this PoC.
- **No mid-chat harness switching.** Intentional, matches Zed.
- **No per-chat agent identity selector at the top of the chat panel,
  no ACP Registry / "Add More Agents" flow.** Both deferred — the
  augmented `+ New chat` dialog already covers chat-creation-time
  selection, and a registry of installable ACP servers is its own
  design problem.

See `docs/superpowers/specs/2026-04-28-acp-bridge-design.md` for the full
design rationale and the developer page below for an architectural map.
