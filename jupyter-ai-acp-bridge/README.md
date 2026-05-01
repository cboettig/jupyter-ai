# jupyter-ai-acp-bridge

A proof-of-concept JupyterLab extension that demonstrates a Zed-style
per-thread ACP harness binding model for Jupyter AI. See the design rationale
at [issue #1558](https://github.com/jupyterlab/jupyter-ai/issues/1558) and the
full design spec at [`docs/superpowers/specs/2026-04-28-acp-bridge-design.md`](../docs/superpowers/specs/2026-04-28-acp-bridge-design.md).

This package is **not on PyPI**. It lives on the `acp-bridge-impl` branch of
the [cboettig/jupyter-ai](https://github.com/cboettig/jupyter-ai) fork to
provide an installable demo people can try without waiting for upstream
agreement on the design.

## What you'll experience

The bridge augments the standard "Create a new chat" dialog with an **Agent**
selector. Pick a harness when you create the chat (Claude Code, OpenCode,
…) and the chat is bound to that harness for its lifetime — the same model
Zed uses for its agent panel. To use a different harness, start a new chat.

Inside a bound chat the input toolbar shows the harness badge plus, when the
harness advertises models, a model `<select>` for picking among them
(Claude Code exposes Default / Sonnet / Haiku). The chat input gets
harness-aware slash-command completion (`/help`, `/permissions`, etc.,
populated from whatever the harness advertises) and `@<filename>` completion
against the workspace.

When the bridge is installed it suppresses the legacy `@`-mention ACP
personas (`@Claude`, `@OpenCode`, …) from `jupyter-ai-acp-client`, since
the bridge supersedes them — both paths end up in the same
`claude-agent-acp` / `opencode` subprocess, so having both surfaces was
confusing. Other Jupyter AI personas (`jupyternaut`, custom user personas)
are unaffected.

This is the architectural pattern. A few pieces are still in progress and
noted under "Known limitations" below.

## Install

You'll want a clean Python environment. The package isn't on PyPI, so install
directly from the branch:

```bash
# Use whatever venv tooling you prefer; uv shown here.
uv venv && source .venv/bin/activate

uv pip install \
  "git+https://github.com/cboettig/jupyter-ai.git@acp-bridge-impl#subdirectory=jupyter-ai-acp-bridge"
```

`pip install` works too if you'd rather:

```bash
python -m venv .venv && source .venv/bin/activate
pip install "git+https://github.com/cboettig/jupyter-ai.git@acp-bridge-impl#subdirectory=jupyter-ai-acp-bridge"
```

This pulls in `jupyter-ai-acp-client`, `jupyter-ai-router`,
`jupyter-ai-persona-manager`, and `jupyterlab-chat` from PyPI as transitive
dependencies, and builds the JupyterLab extension bundle as part of the
install (the build hook calls `jlpm`, so Node.js needs to be available).

Verify the install:

```bash
jupyter server extension list 2>&1 | grep jupyter_ai_acp_bridge
# Expected: jupyter_ai_acp_bridge 0.0.1 OK

jupyter labextension list 2>&1 | grep acp-bridge
# Expected: @jupyter-ai/acp-bridge v0.0.1 enabled OK
```

## Install at least one ACP harness

The bridge is just a UI/protocol layer. To actually talk to a model you need
an ACP harness binary on `PATH`. The demo currently registers two:

- **Claude Code** — needs `claude-agent-acp` on `PATH`. See
  [Claude Code's documentation](https://code.claude.com) for installation;
  authentication via `claude /login` after install.
- **OpenCode** — needs `opencode` on `PATH`. See
  [opencode.ai](https://opencode.ai) for installation; works with any
  configured provider.

You can install one or both. If you only install one, the **Agent** dropdown
in the new-chat dialog will only offer that one.

## Run

```bash
jupyter lab
```

Click **+ New chat** in the chat sidebar (or **Chat** in the launcher).
Pick a harness and a name in the dialog. Send a message. That's the demo.

## Known limitations

This is a PoC, deliberately scoped to demonstrate the architectural pattern.
Concrete in-flight follow-ups, with their TODO links:

1. **Mode and config-option toolbar items not yet rendered.** Only the model
   selector is mounted in the chat input toolbar. The `ModeSelector` and
   `ConfigOptionsSelector` React components exist and the backend state is
   populated, but the Zed-style separate-toolbar-items layout (with mode +
   model hidden when `config_options` is present) is the next deliverable
   (P2 Step 2 in `TODO.md`).

2. **No reactive push for `CurrentModeUpdate` / `ConfigOptionUpdate`.** If
   the agent emits one of these `SessionUpdate` events mid-session (e.g.
   a slash command toggles plan/build), our cached state lags until the
   next `/state` request. Cheap fix is poll-on-focus; push is a follow-up
   (P2 Step 3).

3. **Toolbar-factory conflict with `jupyter-ai-acp-client`.** Both
   packages provide `IInputToolbarRegistryFactory`; only one wins in
   JupyterLab DI. Becomes load-bearing once we add multiple toolbar items
   in P2 Step 2; cleanest fix is upstream in `@jupyter/chat`.

4. **No effort selector, no per-chat agent-identity selector at the top
   of the panel, no ACP Registry / "Add More Agents" flow.** All deferred;
   see `TODO.md` P3.

## Where the code lives

- **Python backend** (per-chat state machine, REST routes, router/persona-manager
  hooks, harness adapters): [`jupyter_ai_acp_bridge/`](jupyter_ai_acp_bridge/)
- **TypeScript frontend** (REST client, React components, augmented
  create-chat dialog): [`src/`](src/)
- **Design spec** (full rationale, alternative-options analysis, decision log):
  [`docs/superpowers/specs/2026-04-28-acp-bridge-design.md`](../docs/superpowers/specs/2026-04-28-acp-bridge-design.md)
- **Implementation plan** (the bite-sized TDD task list this PoC was built from):
  [`docs/superpowers/plans/2026-04-28-acp-bridge-implementation.md`](../docs/superpowers/plans/2026-04-28-acp-bridge-implementation.md)
- **Developer rationale** (architectural map, layering against existing contrib
  packages, gap follow-ups):
  [`docs/source/developers/acp-bridge-rationale.md`](../docs/source/developers/acp-bridge-rationale.md)
- **Live TODO** (what's done / in-flight / deferred): [`TODO.md`](TODO.md)

## Compatibility

- Python ≥ 3.10
- JupyterLab ≥ 4.0
- Node.js (for the build hook at install time)
- Tested against `jupyter-ai-acp-client` 0.1.3, `jupyter-ai-router` 0.0.4,
  `jupyter-ai-persona-manager` 0.0.11, `jupyterlab-chat` 0.21.x.

## Status

PoC. Not maintained as a release artifact. The point is to provide a working
illustration to anchor the discussion on issue #1558. If the design lands
upstream in some form, this fork will be retired in favor of whatever the
upstream maintainers choose to ship.
