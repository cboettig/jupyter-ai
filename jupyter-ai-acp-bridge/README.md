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

After installing, every new Jupyter AI chat starts in a "draft" state with a
harness picker offering whichever ACP harnesses you have on `PATH` (the demo
ships adapters for Claude Code and OpenCode). Picking a harness binds the
chat to it for that chat's lifetime — to use a different harness, start a new
chat. The chat input gets harness-aware slash-command completion (`/help`,
`/permissions`, etc., populated from whatever the harness advertises) and
`@<filename>` completion against the workspace.

This is the architectural pattern. A few things are still stubs and noted
under "Known limitations" below.

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

You can install one or both. If you only install one, the picker will only
offer that one.

## Run

```bash
jupyter lab
```

Open a new chat. Click the harness you want from the picker. Send a message.
That's the demo.

## Known limitations

This is a PoC, deliberately scoped to demonstrate the architectural pattern.
Three pieces are documented gaps with concrete follow-ups:

1. **Toolbar selectors don't auto-attach to the chat input.** The
   `ModelSelector`, `ModeSelector`, and `ConfigOptionsSelector` React
   components are exported from the package and work in isolation, but they
   don't appear in the chat input toolbar yet because `@jupyter/chat` needs
   to expose `IInputToolbarRegistry` as a JupyterFrontEnd token before
   plugins can register toolbar items. **This is itself argument material for
   the upstream proposal** — the Zed-style design needs that small extension
   point to land cleanly.

2. **Model / mode / config-option setters are no-ops.** Issuing the actual
   `acp.SetSessionModelRequest`, `acp.SetSessionModeRequest`, and
   `acp.SetSessionConfigOption*Request` calls requires raw ACP RPC plumbing
   that didn't fit in the PoC budget. The methods exist with TODO comments
   in `jupyter_ai_acp_bridge/harnesses/claude_code.py` and `opencode.py`.

3. **Capability state isn't read from the live session.** Once gap #2 lands,
   `get_session_state()` can populate `available_models`, `session_modes`,
   and `config_options` from the harness's `session/new` response, and the
   selectors will start to populate. Until then, the selectors hide
   themselves (which is the correct production behavior — no advertised
   capability, no UI element).

Once gaps #2 and #3 are closed, a fake-ACP-agent integration test becomes
meaningful and is the next obvious test to add.

## Where the code lives

- **Python backend** (per-chat state machine, REST routes, router/persona-manager
  hooks, harness adapters): [`jupyter_ai_acp_bridge/`](jupyter_ai_acp_bridge/)
- **TypeScript frontend** (REST client, React components, completion providers):
  [`src/`](src/)
- **Design spec** (full rationale, alternative-options analysis, decision log):
  [`docs/superpowers/specs/2026-04-28-acp-bridge-design.md`](../docs/superpowers/specs/2026-04-28-acp-bridge-design.md)
- **Implementation plan** (the bite-sized TDD task list this PoC was built from):
  [`docs/superpowers/plans/2026-04-28-acp-bridge-implementation.md`](../docs/superpowers/plans/2026-04-28-acp-bridge-implementation.md)
- **Developer rationale** (architectural map, layering against existing contrib
  packages, gap follow-ups):
  [`docs/source/developers/acp-bridge-rationale.md`](../docs/source/developers/acp-bridge-rationale.md)

## Compatibility

- Python ≥ 3.10
- JupyterLab ≥ 4.0
- Node.js (for the build hook at install time)
- Tested against `jupyter-ai-acp-client` 0.1.3, `jupyter-ai-router` 0.0.4,
  `jupyter-ai-persona-manager` 0.0.11.

## Status

PoC. Not maintained as a release artifact. The point is to provide a working
illustration to anchor the discussion on issue #1558. If the design lands
upstream in some form, this fork will be retired in favor of whatever the
upstream maintainers choose to ship.
