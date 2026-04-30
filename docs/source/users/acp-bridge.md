# ACP harness selector (preview)

The `jupyter-ai-acp-bridge` package adds a Zed-style per-thread harness
selector to Jupyter AI as a preview. Each new chat is bound to one ACP
harness for its lifetime; switching harness means starting a new chat.

This is a proof-of-concept demonstration of the design proposed in
[issue #1558](https://github.com/jupyterlab/jupyter-ai/issues/1558).
It is additive — installing it does not change the behavior of any
existing personas (jupyternaut, custom user personas, the legacy
`@claude` / `@gemini` ACP personas continue to work as before).

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

1. Open a new chat.
2. The first time you send a message, choose a harness from the picker.
3. Subsequent messages in this chat go to the selected harness.
4. To use a different harness, start a new chat.

## Limitations of the preview

- **Toolbar selectors are not yet attached to the chat input.** The
  `ModelSelector`, `ModeSelector`, and `ConfigOptionsSelector` components
  are exported from the package but do not auto-attach because the
  `@jupyter/chat` package needs to expose `IInputToolbarRegistry` as a
  JupyterFrontEnd token before plugins can register toolbar items. This is
  a small upstream change tracked separately.
- **Model/mode/config setters are stubs.** Reading the live ACP session
  state and issuing `SetSessionModelRequest` / `SetSessionModeRequest` /
  `SetSessionConfigOptionRequest` requires more raw ACP RPC plumbing than
  fit in this PoC. The selector components will hide themselves while the
  underlying capability is unavailable.
- **No mid-thread harness switching.** This matches Zed's behavior; it is
  an intentional design decision documented in the design spec.

See `docs/superpowers/specs/2026-04-28-acp-bridge-design.md` for the full
design rationale, and the developer page below for an architectural map.
