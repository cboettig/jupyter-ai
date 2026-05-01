# ACP bridge: developer guide

A Jupyter AI bridge that gives chats per-thread ACP-harness binding
(Zed-style), rather than the `@`-mention-as-harness model. This is the
canonical orientation doc for anyone editing
[`jupyter-ai-acp-bridge/`](../../../jupyter-ai-acp-bridge/) — it's
denser than the user-facing readme and assumes you've at least skimmed
the design spec at
[`docs/superpowers/specs/2026-04-28-acp-bridge-design.md`](../../superpowers/specs/2026-04-28-acp-bridge-design.md).

> The historical bite-sized TDD task list is at
> [`docs/superpowers/plans/2026-04-28-acp-bridge-implementation.md`](../../superpowers/plans/2026-04-28-acp-bridge-implementation.md).
> That document is **frozen at its 2026-04-28 state** — it traces the
> *initial* implementation. Many specifics (which RPCs to call, where
> selectors mount, etc.) are now obsolete. Refer to this doc for
> current architecture; consult the plan only as a historical record.

> **Conceptual companion:**
> [`personas-as-skills.md`](personas-as-skills.md) — the framing essay
> on how this work sits inside the original Personas vision in
> jupyter-ai, and how Personas align with the
> [Agent Skills](https://agentskills.io/home) open standard.

## Why this exists, briefly

Per [issue #1558](https://github.com/jupyterlab/jupyter-ai/issues/1558):
ACP harnesses shouldn't be exposed as `@`-mentionable personas because
that conflates harness selection with model selection and breaks
per-thread context isolation. A chat is bound to one harness for its
life; capability-driven toolbar selectors (model, session mode,
config options) come straight from what the harness advertises.

The package is purely additive *except* for one suppression: when the
bridge is installed, it suppresses the legacy `@`-mention ACP personas
shipped by `jupyter-ai-acp-client` (`@Claude`, `@OpenCode`, …). They
end up at the same `claude-agent-acp` / `opencode` subprocess as the
bridge does, just via a different surface; having both side-by-side was
confusing in user testing. See [Persona suppression](#persona-suppression)
for the mechanics.

## Module map

### Python (`jupyter_ai_acp_bridge/`)

| Module | Role |
|---|---|
| `extension.py` | `ExtensionApp`. Registers REST routes, instantiates the registry/manager, and schedules `_setup_router_integration()` to attach to `jupyter-ai-router` once it's up. |
| `adapter.py` | `HarnessAdapter` dataclass — static metadata for one harness (id, display_name, icon, executable factory, `persona_class`). |
| `registry.py` | `HarnessRegistry` — in-memory map of `HarnessAdapter`s. |
| `bridge.py` | `ChatBridge` — per-chat state machine (draft → bound, immutable after `bind()`). Owns the per-chat persona instance. |
| `manager.py` | `BridgeManager` — `room_id → ChatBridge` dict. |
| `handlers.py` | Tornado handlers for `/jupyter-ai-acp-bridge/{harnesses, chats/<id>/{bind,state,model,mode,config-option,available-commands}}`. |
| `router_integration.py` | The load-bearing piece: hooks into `jupyter-ai-router` and `jupyter-ai-persona-manager`. See [Router integration](#router-integration). |
| `_capabilities.py` | `AcpBridgeCapabilityMixin` — the real ACP RPC for `set_session_model` / `set_session_mode` / `set_session_config_option`, plus the `get_session_state` payload assembly. |
| `harnesses/claude_code.py`, `harnesses/opencode.py` | Adapter modules. Each defines a `<Harness>BridgePersona(AcpBridgeCapabilityMixin, <upstream>AcpPersona)` and a `HarnessAdapter` instance. |
| `mention_resolver.py` | Pure function that translates `@filename` text to ACP `ContentBlock` dicts. **Currently only unit-tested; not yet wired into the send flow.** |

### TypeScript (`src/`)

| File | Role |
|---|---|
| `index.ts` | Defines six `JupyterFrontEndPlugin`s (`plugin`, `slashPlugin`, `mentionPlugin`, `toolbarPlugin`, `augmentCreatePlugin`). |
| `types.ts` | Types matching the `/state` payload and harness/model/mode/config schemas. |
| `api.ts` | `ServerConnection`-based REST client. |
| `newChat.ts` | `bindWithRetry(chatPath, harnessId)` helper — exponential backoff to handle the chat-init race. |
| `newChatDialog.ts` | The combined name+agent dialog body. |
| `augmentCreate.ts` | Replaces the chat extension's `jupyterlab-chat:create` command with our wrapper. See [Augmented chat creation](#augmented-chat-creation). |
| `components/HarnessHeader.tsx` | Toolbar row composer for bound vs unbound chats. |
| `components/HarnessBadge.tsx` | Read-only label for bound state. |
| `components/HarnessPicker.tsx` | Dropdown picker (button + popover, click-outside dismiss). **Vestigial** — was rendered when the picker lived in the chat-input toolbar; today the augmented `+ New chat` dialog uses vanilla DOM (`newChatDialog.ts`), not this component. Kept exported as a primitive in case it's useful for follow-on work; deletable if it bothers you. |
| `components/ModelSelector.tsx`, `ModeSelector.tsx`, `ConfigOptionsSelector.tsx` | Capability selectors — each self-fetches `/state`, returns null if the capability is empty. |
| `components/HarnessToolbarItem.tsx` | Wrapper that mounts `HarnessHeader` into a chat-input toolbar slot. |
| `providers/BridgeSlashCommandProvider.ts` | `/`-command completion against the bound persona's advertised commands. |
| `providers/BridgeMentionProvider.ts` | `@<filename>` completion against workspace files. |

## Data flows

### Creating a new bound chat

The user clicks **+ New chat** anywhere — sidebar `+`, launcher card,
or command palette. All routes go through the chat extension's
`jupyterlab-chat:create` command, which we've replaced via
`augmentCreate.ts`:

1. Our wrapped `jupyterlab-chat:create` shows the combined Name + Agent
   dialog (`newChatDialog.ts`).
2. Calls the *original* `jupyterlab-chat:create` execute, passing
   `{name: <user-typed>}`. The chat extension honors a pre-supplied
   name and skips its own input-dialog. Returns the new file path.
3. `bindWithRetry(path, harnessId)` POSTs to
   `/jupyter-ai-acp-bridge/chats/<path>/bind`, with exponential backoff:
   the chat file is on disk before the room is registered with
   `file_id_manager` and `persona-managers`, so the first bind attempts
   typically 404 ("Chat not initialized") until the chat-init flow
   has run.
4. Once the bind succeeds the bridge stores `acp_bridge.harness_id` in
   the YChat metadata. That's the source of truth — on reopen we
   restore from it (see next section).

The override touches Lumino's private `CommandRegistry._commands` Map
to remove the existing command entry before re-adding our wrapper.
Stable on `@lumino/commands` 2.x; if a future version renames the
field we log a warning and degrade to the chat extension's name-only
dialog.

### Reopening a previously bound chat

Hitting "open" on an existing `.chat` file goes through `jupyterlab-chat`
→ `jupyter-server-documents` → ydoc handshake → router. The router
fires `chat_init` observers for the room. `BridgeRouterIntegration`
hooks both the chat-init observer and the YChat metadata observer:

```text
chat opens
  → router.connect_chat()
    → notify_chat_init_observers() in registration order
      → BridgeRouterIntegration._on_chat_init()        [runs FIRST]
      → PersonaManagerExtension._on_router_chat_init() [runs SECOND]
        — populates persona_managers[room_id]
```

The trap: **our observer is registered first** (because our
`_setup_router_integration` waits for the router to exist, which
happens before pm-manager finishes its own setup). So
`persona_managers.get(room_id)` returns `None` *during* our observer.
We can't bind there and then because `bridge.bind(adapter, parent=pm)`
needs `pm`.

The fix lives in `_on_chat_init`:

```python
asyncio.get_event_loop().call_soon(
    self._restore_binding_from_metadata, room_id, ychat
)
```

By the time the next event-loop tick runs the deferred restore,
pm-manager's observer has finished and `persona_managers[room_id]` is
populated.

A second trap: jupyterlab-chat's "divergent history → clear YDoc"
recovery wipes `_ymetadata` on connect, so the deferred restore can
still see empty metadata. We additionally subscribe to the metadata
Y-Map's `observe(...)`:

```python
ymeta = getattr(ychat, "_ymetadata", None)
if ymeta is not None and hasattr(ymeta, "observe"):
    def _on_metadata_change(_event):
        loop.call_soon(self._restore_binding_from_metadata, room_id, ychat)
    ymeta.observe(_on_metadata_change)
```

Crucially, the observer schedules via `call_soon` — pycrdt's `observe`
fires synchronously inside the Yjs transaction, and our bind path
itself calls `ychat.set_metadata(...)`, which would re-enter the
observer mid-transaction. Deferring breaks the recursion.

### User submits a message

Two paths, depending on whether the message starts with `/`:

```text
user submits "hi"              user submits "/skill-name [args]"
       │                                │
       ▼                                ▼
 ychat.add_message()              ychat.add_message()
       │                                │
       ▼                                ▼
 router.route_message()           router.route_message()
   first_word starts with /?         first_word starts with /?
   NO → chat_msg_observers           YES → slash_cmd_observers
       │                                │  (after stripping /<cmd>)
       ▼                                ▼
 BridgeRouterIntegration         BridgeRouterIntegration
   ._make_msg_handler()             ._make_slash_msg_handler()
   skip if sender is persona        filter to bound persona's
   skip if message @-mentions         _acp_slash_commands
     a different persona            reconstruct "/<cmd> <args>"
     in pm.personas                 (router stripped the /<cmd>)
       │                                │
       ▼                                ▼
        bridge.dispatch_message(rebuilt)
                  │
                  ▼
       persona.process_message(message)
                  │
                  ▼
       client.prompt_and_reply(text=…)
                  │
                  ▼
        ACP session/prompt → agent
```

The `_make_slash_msg_handler` registration is **load-bearing** —
without it slash commands silently disappear. The router's
`_route_message` peels the `/<cmd>` off the body and dispatches *only*
to `slash_cmd_observers`. A chat-msg observer never sees a slash
message. We register a wildcard pattern (`.*`) and filter inside the
handler against the bound persona's `_acp_slash_commands`, so we
forward only commands the agent advertises (no double-handling of
`/refresh-personas` etc. that other extensions own).

The reconstruction step is also necessary: `claude-agent-acp`'s
slash-skill loader expects to see the literal `/<cmd>` at the start of
the prompt. The router's stripped message body has `/<cmd>` removed.
We re-prepend before dispatch.

## Router integration

`router_integration.py` is where most of the brittle
inter-extension dancing lives.

### Observer registrations

`BridgeRouterIntegration.attach(router)` registers:

- `router.observe_chat_init(self._on_chat_init)` — fires per chat
  open. We install per-chat callbacks here.
- `_on_chat_init` itself registers (per room_id):
  - `router.observe_chat_msg(room_id, self._make_msg_handler(room_id))`
  - `router.observe_slash_cmd_msg(room_id, ".*", self._make_slash_msg_handler(room_id))`
  - `ychat._ymetadata.observe(_on_metadata_change)` — for divergent-history recovery
  - `loop.call_soon(self._restore_binding_from_metadata, room_id, ychat)` — initial restore

### Persona suppression

Three call sites need to clean up:

1. `PersonaManager._ep_persona_classes` (class-level cache). Once
   pruned, future PMs (i.e. new chats opened later) won't instantiate
   the legacy `@`-mention personas at all. Without this we'd be
   playing whack-a-mole on every chat open.
2. `pm.personas` (the dispatch dict). Without this, `PersonaManager.
   on_chat_message` would still route `@Claude` mentions to the legacy
   persona.
3. `pm.ychat._yusers` (the chat's user list). The mention-completion
   provider in the chat extension reads `_yusers` to populate `@`
   suggestions. Without this, even after suppressing dispatch, the
   dropdown still listed `@Claude` / `@OpenCode` / etc.

`_suppress_acp_client_personas()` does all three. It's idempotent and
called from both `_restore_binding_from_metadata` (per chat) and
`bind_chat` (defensive).

The match key is `type(persona).__module__.startswith("jupyter_ai_acp_client.acp_personas")`.
Our own `*BridgePersona` classes live under
`jupyter_ai_acp_bridge.harnesses.*` — they aren't suppressed.

## Persona class layering

A bridge persona has three layers in its MRO:

```python
class ClaudeCodeBridgePersona(
    AcpBridgeCapabilityMixin,
    ClaudeAcpPersona,        # from jupyter_ai_acp_client
):
    pass
```

Order matters. `AcpBridgeCapabilityMixin` is first so its
`get_session_state` / `set_session_*` methods take precedence over any
identically-named methods in upstream. The mixin doesn't override
`process_message` — message dispatch goes through the upstream
`BaseAcpPersona.process_message`, which handles slash-command-detection
in the agent and calls `client.prompt_and_reply` correctly.

## Capability state and ACP RPC

`get_session_state` reads from the cached `NewSessionResponse` returned
by `await self.get_session_response()` (provided by `BaseAcpPersona`):

| `/state` field | Source |
|---|---|
| `available_models` | `response.models.available_models` |
| `selected_model_id` | `_acp_bridge_selected_model_id` instance attr (set after `set_session_model`), falls back to `response.models.current_model_id` |
| `session_modes` | `response.modes.available_modes` |
| `selected_mode_id` | `_acp_bridge_selected_mode_id` instance attr, falls back to `response.modes.current_mode_id` |
| `config_options` | `response.config_options`, flattened with `kind` (Boolean / Select), `category` (the agent's hint, e.g. `'mode'` / `'model'`), `value`, `options[]` |
| `available_commands` | `_acp_slash_commands`, populated from `AvailableCommandsUpdate` SessionUpdate events; `model_dump`'d to flat dicts before serialization |

Setters delegate to `client.get_connection().set_session_model(...)` /
`.set_session_mode(...)` / `.set_config_option(...)`. We track the
selected model / mode locally (instance attrs, lazy) because ACP
doesn't have a `CurrentModelUpdate` event — `set_session_model` is
fire-and-forget, and we'd otherwise lose the fact that we just changed
it on the next `/state` round-trip.

A note on duplication: `claude-agent-acp` advertises *both*
`response.models` / `response.modes` AND duplicates them in
`response.config_options` with `category: 'model'` / `category: 'mode'`.
Zed's `config_state()` picks one or the other; we pick the dedicated
fields and **the `ConfigOptionsSelector` frontend filters out
`category=model`/`category=mode` entries** so the dropdowns aren't
double-rendered.

## Toolbar layout

`HarnessHeader` renders one row inside the chat-input toolbar:

```
[ ModelSelector ▾ ][ ModeSelector ▾ ][ ConfigOptionsSelector items ][ HARNESS-LABEL ]
```

- Each child self-fetches state and returns `null` when its capability
  is absent. So Claude Code shows `model + mode + label`; an
  hypothetical agent that only advertises models shows `model + label`.
- The harness label is at the **end** and styled flat (no border, no
  background, all-caps, muted color) so it reads as a trailing
  identity tag rather than a peer button. Rebinding mid-thread isn't
  supported — making it look unclickable signals that intent.
- The toolbar item itself is registered via the `IInputToolbarRegistryFactory`
  pattern (`toolbarPlugin` in `index.ts`).

When the chat is *unbound* (legacy chats, or anything not created via
the augmented dialog), the header renders an italic hint pointing at
the `+ New chat` button instead.

## Augmented chat creation

`augmentCreatePlugin` replaces `jupyterlab-chat:create` with a wrapper:

```ts
internal.delete(CREATE_CHAT_COMMAND);
app.commands.addCommand(CREATE_CHAT_COMMAND, {
  ...originalMetadata,
  execute: async (args) => {
    if (args?.name) {
      // Programmatic call with a pre-supplied name — skip the dialog
      return original.execute.call(reg, args);
    }
    const choice = await showNewChatDialog(harnesses);
    if (!choice) return null;  // user cancelled
    const path = await original.execute.call(reg, {...args, name: choice.name});
    if (path) bindWithRetry(path, choice.harnessId).catch(console.error);
    return path;
  }
});
```

The args-honoring early return lets internal callers bypass the dialog
(tests and any future programmatic chat creation flows).

## Where to extend

| Want to … | Edit … |
|---|---|
| Add another harness | `jupyter_ai_acp_bridge/harnesses/<name>.py` — subclass the right upstream persona + `AcpBridgeCapabilityMixin`, register a `HarnessAdapter`. |
| Add a per-harness icon | Ship the asset under `style/icons/`, reference from `HarnessAdapter.icon`, then bring back the `<img>` in `HarnessBadge.tsx`. |
| Push reactive mode/config updates | Subscribe to `session_update` events server-side (in `_capabilities.AcpBridgeCapabilityMixin` or a peer `BaseAcpPersona` subclass), mutate the tracked attrs, and add either polling-on-focus or push (websocket / SSE) on the frontend. |
| Render an additional capability | Add a flattening branch in `_capabilities.get_session_state()`, expose it in `ChatBridgeState` (`types.ts`), and add a self-fetching React component that hides on empty (mirror `ModelSelector`). |
| Add a slash command yourself | The agent advertises commands via `AvailableCommandsUpdate`; the user types `/<cmd>`; the bridge forwards to the persona. To intercept *before* the agent sees it, register a competing slash-cmd observer with a more specific pattern. |

## Known gaps and follow-ups

See [`jupyter-ai-acp-bridge/TODO.md`](../../../jupyter-ai-acp-bridge/TODO.md)
for the live list. Recurring themes:

- **No reactive mode/config updates** when the agent toggles them
  internally; UI lags until next `/state` poll. (P2 Step 3)
- **Toolbar-factory conflict with `jupyter-ai-acp-client`** — both
  packages provide `IInputToolbarRegistryFactory`; only one wins in
  JupyterLab DI. Cleanest fix is upstream in `@jupyter/chat`.
- **Image paste (`Ctrl+V`)** — Zed-style direct paste isn't
  implemented; users have to use the chat's attach button. Lives in
  `@jupyter/chat`'s input editor, not in the bridge.
- **No effort selector** — ACP doesn't carry `effort`; Zed has it as a
  hardcoded property of certain Claude model IDs in its
  `language_model` crate. Out of scope for the PoC.
- **No ACP Registry / "Add More Agents"** — Zed's plugin marketplace
  for ACP servers is an entirely separate design.
- **`mention_resolver`** is unit-tested but not yet wired into the
  send path; the harness sees raw `@filename` text and parses it
  itself.
