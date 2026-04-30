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

```
pip install jupyter-ai[acp-bridge]
```

The bridge depends on `jupyter-ai-acp-client`, which provides the underlying
`BaseAcpPersona` runtime that subprocess and ACP-session management is built
on. Currently registered harnesses are Claude Code (requires
`claude-agent-acp` on PATH) and OpenCode (requires `opencode` on PATH).

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
