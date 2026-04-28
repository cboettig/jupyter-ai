# `jupyter-ai-acp-bridge` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working PoC of `jupyter-ai-acp-bridge` per the design at `docs/superpowers/specs/2026-04-28-acp-bridge-design.md`: a per-thread ACP harness binding for Jupyter AI with capability-driven model/mode/config-options selectors and slash/mention pass-through, wired up for one harness (Claude Code).

**Architecture:** New top-level subdirectory `jupyter-ai-acp-bridge/` inside the metapackage fork containing a Jupyter Server extension (Python) and JupyterLab plugin (TypeScript). The Python side wraps the existing `BaseAcpPersona` from `jupyter-ai-acp-client` as a library, manages per-chat harness binding state, and exposes REST routes. The TS side composes existing `@jupyter/chat` extension points (`IInputToolbarRegistryFactory`, `IChatCommandProvider`) for picker, badge, selectors, and completion.

**Tech Stack:** Python 3.10+ (Jupyter Server extension), TypeScript + React (JupyterLab plugin via `@jupyter/chat` extension points), pytest, jest, ACP (`acp` Python package, already a transitive dep via `jupyter-ai-acp-client`).

---

## Working assumptions

- The package lives at `jupyter-ai-acp-bridge/` at the repo root (sibling of `jupyter_ai/`).
- `jupyter-ai-acp-client` is installed in the dev environment so `BaseAcpPersona` and an existing Claude Code adapter class are importable.
- `jupyter-ai-router` and `jupyter-ai-persona-manager` are installed in the dev environment.
- `claude-code-acp` (the Claude Code ACP server binary) is available on PATH for smoke testing.
- The dev environment uses `pip install -e .` (Python) and `jlpm install && jlpm build` (JS) per JupyterLab extension conventions.
- Initial scaffolding is copied from `jupyter-ai-router` (smallest existing contrib package with a similar shape) and renamed.

If any of these are wrong, Phase 0 catches it before code starts.

## File map

```
jupyter-ai-acp-bridge/
├── pyproject.toml
├── package.json
├── tsconfig.json
├── jupyter-config/jupyter_server_config.d/jupyter_ai_acp_bridge.json
├── install.json
├── jupyter_ai_acp_bridge/
│   ├── __init__.py
│   ├── extension.py            # ExtensionApp; registers routes, settings, router hook
│   ├── adapter.py              # HarnessAdapter dataclass
│   ├── registry.py             # HarnessRegistry
│   ├── bridge.py               # ChatBridge (per-chat state machine)
│   ├── manager.py              # BridgeManager (process-wide; per-room ChatBridge map)
│   ├── mention_resolver.py     # text → ACP content blocks
│   ├── handlers.py             # tornado handlers (REST routes)
│   ├── router_integration.py   # router/persona-manager hook (Phase 5)
│   ├── harnesses/
│   │   ├── __init__.py
│   │   └── claude_code.py      # Claude Code HarnessAdapter
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_adapter.py
│       ├── test_registry.py
│       ├── test_bridge.py
│       ├── test_manager.py
│       ├── test_mention_resolver.py
│       ├── test_handlers.py
│       ├── test_router_integration.py
│       └── fake_acp_agent.py   # for integration tests
└── src/
    ├── index.ts                # plugin registration
    ├── api.ts                  # REST client
    ├── types.ts                # TS types matching server payloads
    ├── tokens.ts               # plugin tokens
    ├── components/
    │   ├── HarnessPicker.tsx
    │   ├── HarnessBadge.tsx
    │   ├── ModelSelector.tsx
    │   ├── ModeSelector.tsx
    │   └── ConfigOptionsSelector.tsx
    ├── providers/
    │   ├── BridgeSlashCommandProvider.ts
    │   └── BridgeMentionProvider.ts
    └── __tests__/
        ├── api.test.ts
        ├── HarnessPicker.test.tsx
        └── ModelSelector.test.tsx
```

---

## Phase 0 — Scaffolding

The new package needs a working JupyterLab-extension scaffold before any code can run. The cleanest path is to copy the scaffold from an existing minimal contrib package (`jupyter-ai-router`) and rename. The first commit produces an empty extension that loads cleanly.

### Task 0.1: Verify dev environment

**Files:** none

- [ ] **Step 1: Check Python and Jupyter prerequisites**

```bash
python --version       # expect 3.10+
jupyter --version      # expect Jupyter Server installed
pip show jupyter_ai_acp_client jupyter_ai_router jupyter_ai_persona_manager
which claude-code-acp  # the Claude Code ACP binary; for later smoke test
```

Expected: all three packages report a version. `claude-code-acp` may be missing — if so, note for Phase 6 only.

- [ ] **Step 2: Check JupyterLab extension tooling**

```bash
jlpm --version
node --version
```

Expected: `jlpm` available, Node ≥ 18.

- [ ] **Step 3: Document environment in a scratch note**

Write findings to `jupyter-ai-acp-bridge/SCRATCH.md` (delete before final commit). Note any missing tools.

If any of `jupyter_ai_acp_client`, `jupyter_ai_router`, or `jupyter_ai_persona_manager` are missing, install them with `pip install jupyter-ai-acp-client jupyter-ai-router jupyter-ai-persona-manager` before continuing.

### Task 0.2: Create package skeleton

**Files:** all of `jupyter-ai-acp-bridge/` directory tree

- [ ] **Step 1: Create directory structure**

```bash
cd /home/cboettig/Documents/github/cboettig/jupyter-ai
mkdir -p jupyter-ai-acp-bridge/{jupyter_ai_acp_bridge/{harnesses,tests},src/{components,providers,__tests__},jupyter-config/jupyter_server_config.d,style}
```

- [ ] **Step 2: Verify**

```bash
find jupyter-ai-acp-bridge -type d
```

Expected: lists all directories above.

### Task 0.3: Write `pyproject.toml`

**Files:** Create `jupyter-ai-acp-bridge/pyproject.toml`

- [ ] **Step 1: Write the file**

```toml
[build-system]
requires = ["hatchling>=1.4.0", "jupyterlab>=4.0", "hatch-nodejs-version>=0.3.2"]
build-backend = "hatchling.build"

[project]
name = "jupyter_ai_acp_bridge"
version = "0.0.1"
description = "Per-thread ACP harness binding for Jupyter AI"
readme = "README.md"
license = { text = "BSD-3-Clause" }
requires-python = ">=3.10"
authors = [{ name = "Carl Boettiger", email = "cboettig@berkeley.edu" }]
classifiers = [
  "Framework :: Jupyter",
  "Framework :: Jupyter :: JupyterLab",
  "License :: OSI Approved :: BSD License",
  "Programming Language :: Python :: 3",
]
dependencies = [
  "jupyter_server>=2.0",
  "jupyter_ai_router>=0.0.3",
  "jupyter_ai_persona_manager>=0.0.8",
  "jupyter_ai_acp_client>=0.1.0",
  "jupyterlab_chat>=0.21.0",
]

[project.optional-dependencies]
test = ["pytest>=7", "pytest-asyncio>=0.21", "pytest-tornasync"]

[project.entry-points."jupyter_server.extension_points"]
jupyter_ai_acp_bridge = "jupyter_ai_acp_bridge.extension:AcpBridgeExtension"

[tool.hatch.build.targets.wheel]
packages = ["jupyter_ai_acp_bridge"]

[tool.hatch.build.targets.wheel.shared-data]
"jupyter-config/jupyter_server_config.d" = "etc/jupyter/jupyter_server_config.d"
"install.json" = "share/jupyter/labextensions/@jupyter-ai/acp-bridge/install.json"

[tool.hatch.build.hooks.jupyter-builder]
dependencies = ["hatch-jupyter-builder>=0.5"]
build-function = "hatch_jupyter_builder.npm_builder"

[tool.hatch.build.hooks.jupyter-builder.build-kwargs]
build_cmd = "build:prod"
npm = ["jlpm"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["jupyter_ai_acp_bridge/tests"]
```

- [ ] **Step 2: Write `jupyter-ai-acp-bridge/jupyter-config/jupyter_server_config.d/jupyter_ai_acp_bridge.json`**

```json
{
  "ServerApp": {
    "jpserver_extensions": {
      "jupyter_ai_acp_bridge": true
    }
  }
}
```

- [ ] **Step 3: Write `jupyter-ai-acp-bridge/install.json`**

```json
{
  "packageManager": "python",
  "packageName": "jupyter_ai_acp_bridge",
  "uninstallInstructions": "Use pip uninstall jupyter-ai-acp-bridge."
}
```

- [ ] **Step 4: Write `jupyter-ai-acp-bridge/README.md`**

```markdown
# jupyter-ai-acp-bridge

Per-thread ACP harness binding for Jupyter AI. See the design spec at
`docs/superpowers/specs/2026-04-28-acp-bridge-design.md`.
```

### Task 0.4: Stub Python module

**Files:** Create `jupyter_ai_acp_bridge/__init__.py`, `extension.py`

- [ ] **Step 1: Write `jupyter_ai_acp_bridge/__init__.py`**

```python
"""jupyter-ai-acp-bridge: per-thread ACP harness binding for Jupyter AI."""

__version__ = "0.0.1"


def _jupyter_server_extension_points():
    return [{"module": "jupyter_ai_acp_bridge.extension", "app": "AcpBridgeExtension"}]
```

- [ ] **Step 2: Write minimal `jupyter_ai_acp_bridge/extension.py`**

```python
"""Jupyter Server extension entry point."""
from __future__ import annotations

import time

from jupyter_server.extension.application import ExtensionApp


class AcpBridgeExtension(ExtensionApp):
    name = "jupyter_ai_acp_bridge"
    handlers: list = []

    def initialize_settings(self) -> None:
        start = time.time()
        elapsed = round((time.time() - start) * 1000)
        self.log.info(f"Initialized {self.name} in {elapsed} ms.")
```

- [ ] **Step 3: Install editable and verify it loads**

```bash
cd jupyter-ai-acp-bridge
pip install -e .
jupyter server extension list 2>&1 | grep jupyter_ai_acp_bridge
```

Expected: extension is listed and shows `OK`.

- [ ] **Step 4: Commit**

```bash
git add jupyter-ai-acp-bridge/pyproject.toml jupyter-ai-acp-bridge/install.json \
        jupyter-ai-acp-bridge/jupyter-config jupyter-ai-acp-bridge/README.md \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/__init__.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/extension.py
git commit -m "scaffold jupyter-ai-acp-bridge package"
```

### Task 0.5: Stub TypeScript plugin

**Files:** Create `package.json`, `tsconfig.json`, `src/index.ts`

- [ ] **Step 1: Write `jupyter-ai-acp-bridge/package.json`**

```json
{
  "name": "@jupyter-ai/acp-bridge",
  "version": "0.0.1",
  "description": "Per-thread ACP harness binding for Jupyter AI",
  "main": "lib/index.js",
  "types": "lib/index.d.ts",
  "files": ["lib/**/*.{d.ts,js,js.map,json}", "style/**/*.{css}"],
  "scripts": {
    "build": "jlpm clean && tsc",
    "build:prod": "jlpm clean && tsc",
    "clean": "rimraf lib tsconfig.tsbuildinfo",
    "test": "jest"
  },
  "dependencies": {
    "@jupyter/chat": "^0.16.0",
    "@jupyterlab/application": "^4.0.0",
    "@jupyterlab/coreutils": "^6.0.0",
    "@jupyterlab/services": "^7.0.0",
    "@jupyterlab/ui-components": "^4.0.0",
    "@lumino/widgets": "^2.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@jupyterlab/builder": "^4.0.0",
    "@types/jest": "^29",
    "@types/react": "^18.2.0",
    "jest": "^29",
    "rimraf": "^5",
    "ts-jest": "^29",
    "typescript": "~5.0.0"
  },
  "jupyterlab": {
    "extension": true,
    "outputDir": "jupyter_ai_acp_bridge/labextension"
  }
}
```

- [ ] **Step 2: Write `jupyter-ai-acp-bridge/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2018",
    "module": "esnext",
    "moduleResolution": "node",
    "jsx": "react",
    "strict": true,
    "declaration": true,
    "outDir": "lib",
    "rootDir": "src",
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: Write minimal `jupyter-ai-acp-bridge/src/index.ts`**

```typescript
import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

const PLUGIN_ID = '@jupyter-ai/acp-bridge:plugin';

const plugin: JupyterFrontEndPlugin<void> = {
  id: PLUGIN_ID,
  description: 'Per-thread ACP harness binding for Jupyter AI.',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    console.log('jupyter-ai-acp-bridge loaded');
  }
};

export default plugin;
```

- [ ] **Step 4: Build and verify**

```bash
cd jupyter-ai-acp-bridge
jlpm install
jlpm build
```

Expected: TypeScript compiles, `lib/index.js` exists.

- [ ] **Step 5: Commit**

```bash
git add jupyter-ai-acp-bridge/package.json jupyter-ai-acp-bridge/tsconfig.json \
        jupyter-ai-acp-bridge/src/index.ts jupyter-ai-acp-bridge/.gitignore
echo -e "node_modules/\nlib/\ntsconfig.tsbuildinfo\n*.egg-info/" > jupyter-ai-acp-bridge/.gitignore
git add jupyter-ai-acp-bridge/.gitignore
git commit -m "scaffold TypeScript side of jupyter-ai-acp-bridge"
```

---

## Phase 1 — Python data types

Three small dataclasses and the harness registry, all unit-tested. No external dependencies yet.

### Task 1.1: `HarnessAdapter` dataclass

**Files:** Create `jupyter_ai_acp_bridge/adapter.py`, `tests/test_adapter.py`

- [ ] **Step 1: Write the failing test**

`tests/test_adapter.py`:

```python
from jupyter_ai_acp_bridge.adapter import HarnessAdapter


def test_harness_adapter_required_fields():
    adapter = HarnessAdapter(
        id="claude-code",
        display_name="Claude Code",
        icon="claude.svg",
        executable_factory=lambda: ["claude-code-acp"],
    )
    assert adapter.id == "claude-code"
    assert adapter.display_name == "Claude Code"
    assert adapter.icon == "claude.svg"
    assert adapter.executable_factory() == ["claude-code-acp"]
    assert adapter.env is None
    assert adapter.persona_class is None


def test_harness_adapter_with_persona_class():
    class StubPersona:
        pass

    adapter = HarnessAdapter(
        id="x",
        display_name="X",
        icon="x.svg",
        executable_factory=lambda: ["x"],
        env={"FOO": "bar"},
        persona_class=StubPersona,
    )
    assert adapter.env == {"FOO": "bar"}
    assert adapter.persona_class is StubPersona
```

- [ ] **Step 2: Run test, verify failure**

```bash
pytest jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_adapter.py -v
```

Expected: fails with `ImportError`.

- [ ] **Step 3: Implement `adapter.py`**

```python
"""HarnessAdapter dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class HarnessAdapter:
    """Static metadata for an ACP harness wired to the bridge.

    Intentionally narrow: no model lists, no effort levels, no mode names.
    Everything dynamic comes from the live ACP session.
    """

    id: str
    display_name: str
    icon: str
    executable_factory: Callable[[], list[str]]
    env: Optional[dict[str, str]] = None
    persona_class: Optional[type] = None
```

- [ ] **Step 4: Run test, verify pass**

```bash
pytest jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_adapter.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/adapter.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_adapter.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/__init__.py
git commit -m "add HarnessAdapter dataclass"
```

### Task 1.2: `HarnessRegistry`

**Files:** Create `registry.py`, `tests/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.registry import HarnessRegistry, HarnessNotFoundError


def _make(id_: str = "x") -> HarnessAdapter:
    return HarnessAdapter(
        id=id_,
        display_name=id_.upper(),
        icon=f"{id_}.svg",
        executable_factory=lambda: [id_],
    )


def test_register_and_get():
    registry = HarnessRegistry()
    a = _make("claude-code")
    registry.register(a)
    assert registry.get("claude-code") is a


def test_get_missing_raises():
    registry = HarnessRegistry()
    with pytest.raises(HarnessNotFoundError):
        registry.get("missing")


def test_register_duplicate_raises():
    registry = HarnessRegistry()
    registry.register(_make("a"))
    with pytest.raises(ValueError):
        registry.register(_make("a"))


def test_list_returns_all():
    registry = HarnessRegistry()
    registry.register(_make("a"))
    registry.register(_make("b"))
    ids = sorted(a.id for a in registry.list())
    assert ids == ["a", "b"]
```

- [ ] **Step 2: Run test, verify failure**

```bash
pytest jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_registry.py -v
```

- [ ] **Step 3: Implement `registry.py`**

```python
"""Registry mapping harness id to adapter."""
from __future__ import annotations

from typing import Iterable

from .adapter import HarnessAdapter


class HarnessNotFoundError(KeyError):
    pass


class HarnessRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, HarnessAdapter] = {}

    def register(self, adapter: HarnessAdapter) -> None:
        if adapter.id in self._adapters:
            raise ValueError(f"Harness {adapter.id!r} already registered")
        self._adapters[adapter.id] = adapter

    def get(self, harness_id: str) -> HarnessAdapter:
        try:
            return self._adapters[harness_id]
        except KeyError as exc:
            raise HarnessNotFoundError(harness_id) from exc

    def list(self) -> Iterable[HarnessAdapter]:
        return list(self._adapters.values())
```

- [ ] **Step 4: Run test, verify pass**

```bash
pytest jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_registry.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/registry.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_registry.py
git commit -m "add HarnessRegistry"
```

---

## Phase 2 — `ChatBridge` core

`ChatBridge` owns one chat's binding state, owns the underlying `BaseAcpPersona` instance once bound, and proxies model/mode/config-option ops to ACP. `BridgeManager` is a thin per-room map.

### Task 2.1: `ChatBridge` skeleton + state machine

**Files:** Create `bridge.py`, `tests/test_bridge.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.bridge import ChatBridge, AlreadyBoundError, NotBoundError


def _adapter():
    return HarnessAdapter(
        id="claude-code",
        display_name="Claude Code",
        icon="x.svg",
        executable_factory=lambda: ["claude-code-acp"],
    )


def test_initial_state_is_draft():
    bridge = ChatBridge(chat_id="chat-1")
    assert bridge.is_draft
    assert not bridge.is_bound
    assert bridge.harness_id is None


def test_bind_transitions_to_bound():
    bridge = ChatBridge(chat_id="chat-1")
    bridge.bind(_adapter())
    assert bridge.is_bound
    assert not bridge.is_draft
    assert bridge.harness_id == "claude-code"


def test_double_bind_raises():
    bridge = ChatBridge(chat_id="chat-1")
    bridge.bind(_adapter())
    with pytest.raises(AlreadyBoundError):
        bridge.bind(_adapter())


def test_state_query_when_unbound_raises():
    bridge = ChatBridge(chat_id="chat-1")
    with pytest.raises(NotBoundError):
        bridge.adapter
```

- [ ] **Step 2: Run, verify failure**

```bash
pytest jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_bridge.py -v
```

- [ ] **Step 3: Implement `bridge.py` skeleton**

```python
"""ChatBridge: per-chat harness binding state."""
from __future__ import annotations

from typing import Optional

from .adapter import HarnessAdapter


class AlreadyBoundError(RuntimeError):
    pass


class NotBoundError(RuntimeError):
    pass


class ChatBridge:
    def __init__(self, chat_id: str) -> None:
        self.chat_id = chat_id
        self._adapter: Optional[HarnessAdapter] = None

    @property
    def is_draft(self) -> bool:
        return self._adapter is None

    @property
    def is_bound(self) -> bool:
        return self._adapter is not None

    @property
    def harness_id(self) -> Optional[str]:
        return self._adapter.id if self._adapter else None

    @property
    def adapter(self) -> HarnessAdapter:
        if self._adapter is None:
            raise NotBoundError(f"chat {self.chat_id} has no harness bound")
        return self._adapter

    def bind(self, adapter: HarnessAdapter) -> None:
        if self._adapter is not None:
            raise AlreadyBoundError(
                f"chat {self.chat_id} already bound to {self._adapter.id}"
            )
        self._adapter = adapter
```

- [ ] **Step 4: Run, verify pass**

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/bridge.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_bridge.py
git commit -m "add ChatBridge state machine"
```

### Task 2.2: `BridgeManager` (per-room map)

**Files:** Create `manager.py`, `tests/test_manager.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.manager import BridgeManager


def _adapter(id_: str = "claude-code") -> HarnessAdapter:
    return HarnessAdapter(
        id=id_,
        display_name=id_,
        icon="x.svg",
        executable_factory=lambda: [id_],
    )


def test_get_or_create_returns_same_instance_per_chat():
    mgr = BridgeManager()
    b1 = mgr.get_or_create("chat-1")
    b2 = mgr.get_or_create("chat-1")
    assert b1 is b2


def test_distinct_chats_get_distinct_bridges():
    mgr = BridgeManager()
    b1 = mgr.get_or_create("chat-1")
    b2 = mgr.get_or_create("chat-2")
    assert b1 is not b2


def test_remove_drops_bridge():
    mgr = BridgeManager()
    mgr.get_or_create("chat-1")
    mgr.remove("chat-1")
    assert mgr.lookup("chat-1") is None


def test_lookup_returns_none_if_absent():
    mgr = BridgeManager()
    assert mgr.lookup("missing") is None
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement `manager.py`**

```python
"""BridgeManager: process-wide map of chat_id -> ChatBridge."""
from __future__ import annotations

from typing import Optional

from .bridge import ChatBridge


class BridgeManager:
    def __init__(self) -> None:
        self._bridges: dict[str, ChatBridge] = {}

    def get_or_create(self, chat_id: str) -> ChatBridge:
        if chat_id not in self._bridges:
            self._bridges[chat_id] = ChatBridge(chat_id=chat_id)
        return self._bridges[chat_id]

    def lookup(self, chat_id: str) -> Optional[ChatBridge]:
        return self._bridges.get(chat_id)

    def remove(self, chat_id: str) -> None:
        self._bridges.pop(chat_id, None)
```

- [ ] **Step 4: Verify pass**

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/manager.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_manager.py
git commit -m "add BridgeManager"
```

### Task 2.3: Persist `harness_id` to chat metadata on bind

**Files:** Modify `bridge.py`, extend `tests/test_bridge.py`

- [ ] **Step 1: Add a failing test**

Append to `tests/test_bridge.py`:

```python
class _FakeYChat:
    def __init__(self) -> None:
        self._meta: dict = {}

    def get_metadata(self) -> dict:
        return self._meta

    def set_metadata(self, key: str, value) -> None:
        self._meta[key] = value


def test_bind_writes_metadata():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    bridge.bind(_adapter())
    assert ychat.get_metadata().get("acp_bridge") == {"harness_id": "claude-code"}


def test_construct_with_existing_metadata_restores_binding():
    ychat = _FakeYChat()
    ychat.set_metadata("acp_bridge", {"harness_id": "claude-code"})
    # registry is needed to resolve harness_id -> adapter
    from jupyter_ai_acp_bridge.registry import HarnessRegistry
    registry = HarnessRegistry()
    registry.register(_adapter())
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat, registry=registry)
    assert bridge.is_bound
    assert bridge.harness_id == "claude-code"
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Update `bridge.py`**

```python
from __future__ import annotations

from typing import Any, Optional

from .adapter import HarnessAdapter

METADATA_KEY = "acp_bridge"


class AlreadyBoundError(RuntimeError):
    pass


class NotBoundError(RuntimeError):
    pass


class ChatBridge:
    def __init__(
        self,
        chat_id: str,
        ychat: Optional[Any] = None,
        registry: Optional[Any] = None,
    ) -> None:
        self.chat_id = chat_id
        self.ychat = ychat
        self._adapter: Optional[HarnessAdapter] = None
        if ychat is not None and registry is not None:
            existing = ychat.get_metadata().get(METADATA_KEY)
            if existing and "harness_id" in existing:
                self._adapter = registry.get(existing["harness_id"])

    @property
    def is_draft(self) -> bool:
        return self._adapter is None

    @property
    def is_bound(self) -> bool:
        return self._adapter is not None

    @property
    def harness_id(self) -> Optional[str]:
        return self._adapter.id if self._adapter else None

    @property
    def adapter(self) -> HarnessAdapter:
        if self._adapter is None:
            raise NotBoundError(f"chat {self.chat_id} has no harness bound")
        return self._adapter

    def bind(self, adapter: HarnessAdapter) -> None:
        if self._adapter is not None:
            raise AlreadyBoundError(
                f"chat {self.chat_id} already bound to {self._adapter.id}"
            )
        self._adapter = adapter
        if self.ychat is not None:
            self.ychat.set_metadata(METADATA_KEY, {"harness_id": adapter.id})
```

- [ ] **Step 4: Verify pass**

```bash
pytest jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_bridge.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/bridge.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_bridge.py
git commit -m "persist harness binding to chat metadata"
```

### Task 2.4: Wrap `BaseAcpPersona` instance on bind

This is the integration point with `jupyter-ai-acp-client`. The persona class lives in the adapter; binding instantiates it (or reuses a class-level subprocess as `BaseAcpPersona` already supports). The persona instance is the runtime ACP client for the chat.

**Files:** Modify `bridge.py`, extend `tests/test_bridge.py` with a fake persona class

- [ ] **Step 1: Write the failing test**

```python
class _FakePersona:
    last_kwargs: dict = {}

    def __init__(self, *, parent=None, ychat=None, **kwargs):
        _FakePersona.last_kwargs = {"parent": parent, "ychat": ychat, **kwargs}
        self.parent = parent
        self.ychat = ychat


def test_bind_instantiates_persona():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    adapter = HarnessAdapter(
        id="claude-code",
        display_name="Claude Code",
        icon="x.svg",
        executable_factory=lambda: ["claude-code-acp"],
        persona_class=_FakePersona,
    )
    bridge.bind(adapter, parent=object())
    assert bridge.persona is not None
    assert bridge.persona.ychat is ychat
    assert _FakePersona.last_kwargs.get("executable") == ["claude-code-acp"]


def test_bind_without_persona_class_keeps_persona_none():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    adapter = _adapter()  # no persona_class
    bridge.bind(adapter, parent=object())
    assert bridge.persona is None
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Update `bridge.py`**

```python
def bind(self, adapter: HarnessAdapter, *, parent: Any = None) -> None:
    if self._adapter is not None:
        raise AlreadyBoundError(
            f"chat {self.chat_id} already bound to {self._adapter.id}"
        )
    self._adapter = adapter
    self._persona = None
    if adapter.persona_class is not None:
        self._persona = adapter.persona_class(
            parent=parent,
            ychat=self.ychat,
            executable=adapter.executable_factory(),
        )
    if self.ychat is not None:
        self.ychat.set_metadata(METADATA_KEY, {"harness_id": adapter.id})


@property
def persona(self) -> Any:
    return getattr(self, "_persona", None)
```

Add `self._persona: Optional[Any] = None` initialization in `__init__`.

- [ ] **Step 4: Verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "instantiate wrapped persona class on bind"
```

### Task 2.5: Add `dispatch_message`, `set_model`, `set_mode`, `set_config_option`

These delegate to the wrapped persona. For the PoC, the methods invoke methods on the underlying `JaiAcpClient` exposed via the persona. We mock the persona for unit tests.

**Files:** Modify `bridge.py`, extend `tests/test_bridge.py`

- [ ] **Step 1: Write tests**

```python
import asyncio


class _AsyncFakePersona:
    """A fake persona that records what was called."""
    def __init__(self, *, parent=None, ychat=None, executable=None, **kwargs):
        self.processed: list = []
        self.model_set: list = []
        self.mode_set: list = []
        self.config_set: list = []

    async def process_message(self, message):
        self.processed.append(message)

    # Methods we'll add for capability ops:
    async def get_session_state(self):
        return {
            "selected_model_id": "sonnet-4-5",
            "available_models": [{"id": "sonnet-4-5", "name": "Sonnet 4.5"}],
            "selected_mode_id": "default",
            "session_modes": [{"id": "default", "name": "Default"}],
            "config_options": [],
            "available_commands": [{"name": "/help", "description": "help"}],
        }

    async def set_session_model(self, model_id):
        self.model_set.append(model_id)

    async def set_session_mode(self, mode_id):
        self.mode_set.append(mode_id)

    async def set_session_config_option(self, option_id, value):
        self.config_set.append((option_id, value))


def test_dispatch_message_calls_persona():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    adapter = HarnessAdapter(
        id="claude-code",
        display_name="x",
        icon="x.svg",
        executable_factory=lambda: ["x"],
        persona_class=_AsyncFakePersona,
    )
    bridge.bind(adapter, parent=object())
    msg = object()
    asyncio.run(bridge.dispatch_message(msg))
    assert bridge.persona.processed == [msg]


def test_set_model_delegates():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    adapter = HarnessAdapter(
        id="claude-code",
        display_name="x",
        icon="x.svg",
        executable_factory=lambda: ["x"],
        persona_class=_AsyncFakePersona,
    )
    bridge.bind(adapter, parent=object())
    asyncio.run(bridge.set_model("opus-4"))
    assert bridge.persona.model_set == ["opus-4"]


def test_get_state_returns_dict_when_bound():
    ychat = _FakeYChat()
    bridge = ChatBridge(chat_id="chat-1", ychat=ychat)
    adapter = HarnessAdapter(
        id="claude-code",
        display_name="x",
        icon="x.svg",
        executable_factory=lambda: ["x"],
        persona_class=_AsyncFakePersona,
    )
    bridge.bind(adapter, parent=object())
    state = asyncio.run(bridge.get_state())
    assert state["harness_id"] == "claude-code"
    assert state["selected_model_id"] == "sonnet-4-5"
    assert any(m["id"] == "sonnet-4-5" for m in state["available_models"])


def test_get_state_when_unbound():
    bridge = ChatBridge(chat_id="chat-1")
    state = asyncio.run(bridge.get_state())
    assert state == {"harness_id": None}
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement methods on `ChatBridge`**

```python
async def dispatch_message(self, message: Any) -> None:
    if self._persona is None:
        raise NotBoundError("no persona to dispatch to")
    await self._persona.process_message(message)

async def get_state(self) -> dict:
    if not self.is_bound:
        return {"harness_id": None}
    persona = self._persona
    base = {"harness_id": self._adapter.id}
    if persona is None or not hasattr(persona, "get_session_state"):
        return base
    return {**base, **(await persona.get_session_state())}

async def set_model(self, model_id: str) -> None:
    if self._persona is None:
        raise NotBoundError("no persona")
    await self._persona.set_session_model(model_id)

async def set_mode(self, mode_id: str) -> None:
    if self._persona is None:
        raise NotBoundError("no persona")
    await self._persona.set_session_mode(mode_id)

async def set_config_option(self, option_id: str, value: Any) -> None:
    if self._persona is None:
        raise NotBoundError("no persona")
    await self._persona.set_session_config_option(option_id, value)
```

> **Implementation note for Phase 6 (Claude Code adapter):** the methods
> `get_session_state`, `set_session_model`, `set_session_mode`,
> `set_session_config_option` need to exist on the wrapped persona class. If
> `BaseAcpPersona` (or `ClaudeCodeAcpPersona`) does not already expose these,
> the adapter task in Phase 6 thinly wraps them by talking to the underlying
> `JaiAcpClient`. The unit tests above use a fake persona, so this Phase 2
> code is unblocked.

- [ ] **Step 4: Verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "add ChatBridge dispatch + capability ops"
```

---

## Phase 3 — Mention resolver

Translates a chat input string into ACP `ContentBlock`s. Persona-name mentions are passed through as plain text.

### Task 3.1: ContentBlock helper types and resolver skeleton

**Files:** Create `mention_resolver.py`, `tests/test_mention_resolver.py`

- [ ] **Step 1: Write tests**

```python
from jupyter_ai_acp_bridge.mention_resolver import resolve_mentions, ContentBlock


def test_plain_text_returns_single_text_block():
    blocks = resolve_mentions("hello world", persona_names={"jupyternaut"})
    assert blocks == [{"type": "text", "text": "hello world"}]


def test_persona_mention_left_as_plain_text():
    blocks = resolve_mentions("@jupyternaut summarize", persona_names={"jupyternaut"})
    assert blocks == [{"type": "text", "text": "@jupyternaut summarize"}]


def test_filepath_mention_becomes_resource_link():
    blocks = resolve_mentions(
        "look at @README.md please",
        persona_names=set(),
        cwd="/tmp/proj",
        file_resolver=lambda p: f"/tmp/proj/{p}" if p == "README.md" else None,
    )
    # expect: text "look at ", ResourceLink, text " please"
    assert len(blocks) == 3
    assert blocks[0] == {"type": "text", "text": "look at "}
    assert blocks[1] == {
        "type": "resource_link",
        "uri": "file:///tmp/proj/README.md",
        "name": "README.md",
    }
    assert blocks[2] == {"type": "text", "text": " please"}


def test_unresolved_at_word_left_as_text():
    blocks = resolve_mentions(
        "what is @nonexistent",
        persona_names=set(),
        cwd="/tmp",
        file_resolver=lambda p: None,
    )
    assert blocks == [{"type": "text", "text": "what is @nonexistent"}]
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement `mention_resolver.py`**

```python
"""Translate input strings to ACP content blocks."""
from __future__ import annotations

import re
from typing import Callable, Optional, TypedDict, Union

# Approximate ACP content block JSON shapes (we emit plain dicts;
# the persona / acp lib serializes them).
ContentBlock = dict

_MENTION_RE = re.compile(r"@([\w./-]+)")


def resolve_mentions(
    text: str,
    *,
    persona_names: set[str],
    cwd: Optional[str] = None,
    file_resolver: Optional[Callable[[str], Optional[str]]] = None,
) -> list[ContentBlock]:
    """Return a list of ACP content-block dicts.

    Persona-name mentions are *not* resolved; they remain inline text so the
    server-side router can intercept them.
    """
    if not text:
        return [{"type": "text", "text": ""}]

    blocks: list[ContentBlock] = []
    cursor = 0
    for match in _MENTION_RE.finditer(text):
        name = match.group(1)
        # If it's a registered persona, leave inline.
        if name in persona_names:
            continue
        # Try file resolution.
        resolved: Optional[str] = None
        if file_resolver is not None:
            resolved = file_resolver(name)
        if resolved is None:
            continue  # unresolved -> leave inline
        # Emit preceding text (including the @ prefix? no — replace the whole match)
        if match.start() > cursor:
            blocks.append({"type": "text", "text": text[cursor:match.start()]})
        blocks.append(
            {
                "type": "resource_link",
                "uri": f"file://{resolved}",
                "name": name,
            }
        )
        cursor = match.end()
    if cursor < len(text):
        blocks.append({"type": "text", "text": text[cursor:]})

    if not blocks:
        return [{"type": "text", "text": text}]
    # Coalesce empty trailing/leading text blocks
    return [b for b in blocks if not (b["type"] == "text" and b["text"] == "")]
```

- [ ] **Step 4: Verify pass**

- [ ] **Step 5: Commit**

```bash
git add jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/mention_resolver.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_mention_resolver.py
git commit -m "add mention resolver"
```

### Task 3.2: `@notebook` and `@cell` resolvers

These wrap the file resolver concept with Jupyter-specific resources. For the PoC we accept that "active notebook" / "active cell" are looked up by the *frontend* and serialized into the chat input as `@<path>` / `@cell:<id>` tokens, so the server-side resolver only needs to handle the token forms.

**Files:** Modify `mention_resolver.py`, extend test file

- [ ] **Step 1: Write tests**

```python
def test_cell_token_becomes_resource_block():
    def cell_resolver(cell_id: str):
        if cell_id == "abc123":
            return {"notebook_path": "/p/n.ipynb", "source": "print(1)"}
        return None

    blocks = resolve_mentions(
        "explain @cell:abc123 please",
        persona_names=set(),
        cell_resolver=cell_resolver,
    )
    assert any(b.get("type") == "resource" for b in blocks)
    res = next(b for b in blocks if b["type"] == "resource")
    assert res["uri"] == "jupyter-cell:///p/n.ipynb#abc123"
    assert res["text"] == "print(1)"
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Add `cell_resolver` parameter**

Update `_MENTION_RE` to also match `@cell:<id>`:

```python
_MENTION_RE = re.compile(r"@(cell:[\w-]+|[\w./-]+)")
```

In the loop, before file resolver:

```python
if name.startswith("cell:") and cell_resolver is not None:
    cell_id = name[len("cell:"):]
    cell_info = cell_resolver(cell_id)
    if cell_info is not None:
        if match.start() > cursor:
            blocks.append({"type": "text", "text": text[cursor:match.start()]})
        blocks.append(
            {
                "type": "resource",
                "uri": f"jupyter-cell://{cell_info['notebook_path']}#{cell_id}",
                "text": cell_info["source"],
            }
        )
        cursor = match.end()
        continue
```

Add `cell_resolver: Optional[Callable[[str], Optional[dict]]] = None` to the function signature.

- [ ] **Step 4: Verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "add @cell resolution to mention resolver"
```

---

## Phase 4 — REST routes

Tornado handlers for the endpoints listed in spec §4.1. Each route hits the bridge manager, then serializes the response.

### Task 4.1: `GET /jupyter-ai-acp-bridge/harnesses`

**Files:** Create `handlers.py`, `tests/test_handlers.py`, modify `extension.py`

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.registry import HarnessRegistry
from jupyter_ai_acp_bridge.manager import BridgeManager
from jupyter_ai_acp_bridge.handlers import HarnessesHandler


class HarnessesHandlerTest(AsyncHTTPTestCase):
    def get_app(self) -> Application:
        registry = HarnessRegistry()
        registry.register(HarnessAdapter(
            id="claude-code", display_name="Claude Code", icon="claude.svg",
            executable_factory=lambda: ["claude-code-acp"],
        ))
        return Application(
            [(r"/harnesses", HarnessesHandler, dict(
                registry=registry, bridge_manager=BridgeManager(),
            ))]
        )

    def test_lists_harnesses(self):
        resp = self.fetch("/harnesses")
        assert resp.code == 200
        body = json.loads(resp.body)
        assert body == {
            "harnesses": [
                {"id": "claude-code", "display_name": "Claude Code", "icon": "claude.svg"}
            ]
        }
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement `handlers.py` with `HarnessesHandler`**

```python
"""Tornado handlers exposing bridge state via REST."""
from __future__ import annotations

import json
from typing import Any

from tornado.web import RequestHandler

from .manager import BridgeManager
from .registry import HarnessNotFoundError, HarnessRegistry


class _BridgeBaseHandler(RequestHandler):
    def initialize(
        self, registry: HarnessRegistry, bridge_manager: BridgeManager
    ) -> None:
        self.registry = registry
        self.bridge_manager = bridge_manager

    def write_json(self, payload: Any) -> None:
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(payload))


class HarnessesHandler(_BridgeBaseHandler):
    def get(self) -> None:
        self.write_json({
            "harnesses": [
                {"id": h.id, "display_name": h.display_name, "icon": h.icon}
                for h in self.registry.list()
            ]
        })
```

- [ ] **Step 4: Verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "add HarnessesHandler"
```

### Task 4.2: `POST /jupyter-ai-acp-bridge/chats/{chat_id}/bind`

**Files:** Modify `handlers.py`, extend tests

- [ ] **Step 1: Write the failing test**

```python
class BindHandlerTest(AsyncHTTPTestCase):
    def get_app(self):
        registry = HarnessRegistry()
        registry.register(HarnessAdapter(
            id="claude-code", display_name="Claude Code", icon="x.svg",
            executable_factory=lambda: ["x"],
        ))
        self.bridge_manager = BridgeManager()
        return Application(
            [(r"/chats/([^/]+)/bind", BindHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager,
            ))]
        )

    def test_bind_creates_binding(self):
        resp = self.fetch(
            "/chats/chat-1/bind",
            method="POST",
            body=json.dumps({"harness_id": "claude-code"}),
        )
        assert resp.code == 200
        body = json.loads(resp.body)
        assert body["harness_id"] == "claude-code"

    def test_bind_unknown_harness_returns_404(self):
        resp = self.fetch(
            "/chats/chat-1/bind",
            method="POST",
            body=json.dumps({"harness_id": "nope"}),
        )
        assert resp.code == 404

    def test_double_bind_returns_409(self):
        self.fetch(
            "/chats/chat-1/bind", method="POST",
            body=json.dumps({"harness_id": "claude-code"}),
        )
        resp = self.fetch(
            "/chats/chat-1/bind", method="POST",
            body=json.dumps({"harness_id": "claude-code"}),
        )
        assert resp.code == 409
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement `BindHandler`**

```python
from .bridge import AlreadyBoundError


class BindHandler(_BridgeBaseHandler):
    def post(self, chat_id: str) -> None:
        try:
            payload = json.loads(self.request.body or b"{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write_json({"error": "invalid JSON"})
            return
        harness_id = payload.get("harness_id")
        if not harness_id:
            self.set_status(400)
            self.write_json({"error": "missing harness_id"})
            return
        try:
            adapter = self.registry.get(harness_id)
        except HarnessNotFoundError:
            self.set_status(404)
            self.write_json({"error": f"unknown harness {harness_id!r}"})
            return
        bridge = self.bridge_manager.get_or_create(chat_id)
        try:
            bridge.bind(adapter)
        except AlreadyBoundError as exc:
            self.set_status(409)
            self.write_json({"error": str(exc)})
            return
        self.write_json({"harness_id": harness_id})
```

- [ ] **Step 4: Verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "add BindHandler"
```

### Task 4.3: `GET /chats/{chat_id}/state`

**Files:** Modify `handlers.py`, extend tests

- [ ] **Step 1: Write test**

```python
class StateHandlerTest(AsyncHTTPTestCase):
    def get_app(self):
        registry = HarnessRegistry()
        self.bridge_manager = BridgeManager()
        return Application(
            [(r"/chats/([^/]+)/state", StateHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager,
            ))]
        )

    def test_unbound_returns_null(self):
        resp = self.fetch("/chats/chat-1/state")
        assert resp.code == 200
        body = json.loads(resp.body)
        assert body == {"harness_id": None}
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement**

```python
class StateHandler(_BridgeBaseHandler):
    async def get(self, chat_id: str) -> None:
        bridge = self.bridge_manager.lookup(chat_id)
        if bridge is None:
            self.write_json({"harness_id": None})
            return
        state = await bridge.get_state()
        self.write_json(state)
```

- [ ] **Step 4: Verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "add StateHandler"
```

### Task 4.4: Set-model / set-mode / set-config-option / available-commands

These four are structurally identical: parse JSON body, look up bridge, delegate to a bridge method. Implement together, one test class with four tests.

**Files:** Modify `handlers.py`, extend tests

- [ ] **Step 1: Write tests**

```python
from .test_bridge import _AsyncFakePersona  # reuse fake persona from Phase 2 tests

from jupyter_ai_acp_bridge.handlers import (
    ModelHandler,
    ModeHandler,
    ConfigOptionHandler,
    AvailableCommandsHandler,
)


class CapabilityHandlerTests(AsyncHTTPTestCase):
    def get_app(self):
        registry = HarnessRegistry()
        adapter = HarnessAdapter(
            id="claude-code", display_name="x", icon="x.svg",
            executable_factory=lambda: ["x"],
            persona_class=_AsyncFakePersona,
        )
        registry.register(adapter)
        self.bridge_manager = BridgeManager()
        # Pre-bind chat-1
        bridge = self.bridge_manager.get_or_create("chat-1")
        bridge.bind(adapter, parent=object())
        self.bridge = bridge
        return Application([
            (r"/chats/([^/]+)/model", ModelHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/mode", ModeHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/config-option", ConfigOptionHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
            (r"/chats/([^/]+)/available-commands", AvailableCommandsHandler, dict(
                registry=registry, bridge_manager=self.bridge_manager)),
        ])

    def test_set_model(self):
        resp = self.fetch(
            "/chats/chat-1/model", method="POST",
            body=json.dumps({"model_id": "opus-4"}),
        )
        assert resp.code == 200
        assert self.bridge.persona.model_set == ["opus-4"]

    def test_set_mode(self):
        resp = self.fetch(
            "/chats/chat-1/mode", method="POST",
            body=json.dumps({"mode_id": "plan"}),
        )
        assert resp.code == 200
        assert self.bridge.persona.mode_set == ["plan"]

    def test_set_config_option(self):
        resp = self.fetch(
            "/chats/chat-1/config-option", method="POST",
            body=json.dumps({"option_id": "verbose", "value": True}),
        )
        assert resp.code == 200
        assert self.bridge.persona.config_set == [("verbose", True)]

    def test_available_commands(self):
        resp = self.fetch("/chats/chat-1/available-commands")
        assert resp.code == 200
        body = json.loads(resp.body)
        assert body["commands"] == [{"name": "/help", "description": "help"}]
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement the four handlers**

```python
class ModelHandler(_BridgeBaseHandler):
    async def post(self, chat_id: str) -> None:
        payload = json.loads(self.request.body or b"{}")
        bridge = self.bridge_manager.lookup(chat_id)
        if bridge is None or not bridge.is_bound:
            self.set_status(404); self.write_json({"error": "no bridge"}); return
        await bridge.set_model(payload["model_id"])
        self.write_json({"ok": True})


class ModeHandler(_BridgeBaseHandler):
    async def post(self, chat_id: str) -> None:
        payload = json.loads(self.request.body or b"{}")
        bridge = self.bridge_manager.lookup(chat_id)
        if bridge is None or not bridge.is_bound:
            self.set_status(404); self.write_json({"error": "no bridge"}); return
        await bridge.set_mode(payload["mode_id"])
        self.write_json({"ok": True})


class ConfigOptionHandler(_BridgeBaseHandler):
    async def post(self, chat_id: str) -> None:
        payload = json.loads(self.request.body or b"{}")
        bridge = self.bridge_manager.lookup(chat_id)
        if bridge is None or not bridge.is_bound:
            self.set_status(404); self.write_json({"error": "no bridge"}); return
        await bridge.set_config_option(payload["option_id"], payload["value"])
        self.write_json({"ok": True})


class AvailableCommandsHandler(_BridgeBaseHandler):
    async def get(self, chat_id: str) -> None:
        bridge = self.bridge_manager.lookup(chat_id)
        if bridge is None or not bridge.is_bound:
            self.write_json({"commands": []}); return
        state = await bridge.get_state()
        self.write_json({"commands": state.get("available_commands", [])})
```

- [ ] **Step 4: Verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "add capability handlers (model/mode/config/commands)"
```

### Task 4.5: Wire handlers into `extension.py`

**Files:** Modify `extension.py`

- [ ] **Step 1: Update `extension.py`**

```python
from __future__ import annotations

import time
from typing import Any

from jupyter_server.extension.application import ExtensionApp

from .handlers import (
    AvailableCommandsHandler,
    BindHandler,
    ConfigOptionHandler,
    HarnessesHandler,
    ModeHandler,
    ModelHandler,
    StateHandler,
)
from .manager import BridgeManager
from .registry import HarnessRegistry


URL = r"/jupyter-ai-acp-bridge"


class AcpBridgeExtension(ExtensionApp):
    name = "jupyter_ai_acp_bridge"
    handlers: list = []  # populated in initialize_settings

    registry: HarnessRegistry
    bridge_manager: BridgeManager

    def initialize_settings(self) -> None:
        start = time.time()
        self.registry = HarnessRegistry()
        self.bridge_manager = BridgeManager()

        # Register the package's own harness adapters
        from .harnesses.claude_code import register as register_claude_code
        register_claude_code(self.registry)

        # Make registry / manager available to other extensions
        if "jupyter-ai" not in self.settings:
            self.settings["jupyter-ai"] = {}
        self.settings["jupyter-ai"]["acp-bridge-registry"] = self.registry
        self.settings["jupyter-ai"]["acp-bridge-manager"] = self.bridge_manager

        kwargs = {"registry": self.registry, "bridge_manager": self.bridge_manager}
        self.handlers = [
            (URL + r"/harnesses", HarnessesHandler, kwargs),
            (URL + r"/chats/([^/]+)/bind", BindHandler, kwargs),
            (URL + r"/chats/([^/]+)/state", StateHandler, kwargs),
            (URL + r"/chats/([^/]+)/model", ModelHandler, kwargs),
            (URL + r"/chats/([^/]+)/mode", ModeHandler, kwargs),
            (URL + r"/chats/([^/]+)/config-option", ConfigOptionHandler, kwargs),
            (URL + r"/chats/([^/]+)/available-commands", AvailableCommandsHandler, kwargs),
        ]

        elapsed = round((time.time() - start) * 1000)
        self.log.info(f"Initialized {self.name} in {elapsed} ms.")
```

- [ ] **Step 2: Run server and curl-smoke-test**

```bash
jupyter server --no-browser &
SERVER_PID=$!
sleep 3
TOKEN=$(jupyter server list 2>&1 | head -2 | tail -1 | sed 's/.*token=//; s/ .*//')
curl -s "http://localhost:8888/jupyter-ai-acp-bridge/harnesses?token=$TOKEN"
kill $SERVER_PID
```

Expected: returns `{"harnesses": [{"id": "claude-code", ...}]}` (assuming Phase 6 is done; if not, returns `{"harnesses": []}`).

- [ ] **Step 3: Commit**

```bash
git commit -am "wire bridge routes into Jupyter Server extension"
```

---

## Phase 5 — Router & persona-manager integration

The bridge registers a chat-init observer with `jupyter-ai-router`. On chat init, it installs a chat-msg observer that dispatches to the bridge when the chat has a bound harness, and configures the per-chat `PersonaManager` to suppress its default-persona fallback.

### Task 5.1: Hook into router for chat init

**Files:** Modify `extension.py`, create `router_integration.py`, `tests/test_router_integration.py`

- [ ] **Step 1: Write a unit test against a fake router**

```python
import asyncio

from jupyter_ai_acp_bridge.adapter import HarnessAdapter
from jupyter_ai_acp_bridge.manager import BridgeManager
from jupyter_ai_acp_bridge.registry import HarnessRegistry
from jupyter_ai_acp_bridge.router_integration import BridgeRouterIntegration


class _FakeRouter:
    def __init__(self):
        self.chat_init_observers = []
        self.chat_msg_observers = {}

    def observe_chat_init(self, cb):
        self.chat_init_observers.append(cb)

    def observe_chat_msg(self, room_id, cb):
        self.chat_msg_observers.setdefault(room_id, []).append(cb)


class _FakeYChat:
    def __init__(self):
        self._meta = {}

    def get_metadata(self):
        return self._meta

    def set_metadata(self, k, v):
        self._meta[k] = v


def test_chat_init_installs_chat_msg_observer():
    router = _FakeRouter()
    integration = BridgeRouterIntegration(
        registry=HarnessRegistry(), bridge_manager=BridgeManager(),
        persona_managers={},
    )
    integration.attach(router)
    # Trigger chat init
    ychat = _FakeYChat()
    for cb in router.chat_init_observers:
        cb("chat-1", ychat)
    assert "chat-1" in router.chat_msg_observers
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement `router_integration.py`**

```python
"""Bridge integration with jupyter-ai-router."""
from __future__ import annotations

from typing import Any

from .manager import BridgeManager
from .registry import HarnessRegistry


class BridgeRouterIntegration:
    def __init__(
        self,
        *,
        registry: HarnessRegistry,
        bridge_manager: BridgeManager,
        persona_managers: dict[str, Any],
    ) -> None:
        self.registry = registry
        self.bridge_manager = bridge_manager
        self.persona_managers = persona_managers

    def attach(self, router: Any) -> None:
        router.observe_chat_init(self._on_chat_init)

    def _on_chat_init(self, room_id: str, ychat: Any) -> None:
        # Lazily create a ChatBridge backed by ychat metadata.
        bridge = self.bridge_manager.get_or_create(room_id)
        bridge.ychat = ychat
        # Restore binding from metadata if present.
        meta = ychat.get_metadata().get("acp_bridge")
        if meta and "harness_id" in meta:
            try:
                adapter = self.registry.get(meta["harness_id"])
                if bridge.is_draft:
                    bridge.bind(adapter)
            except Exception:
                pass
        router.observe_chat_msg(room_id, self._make_msg_handler(room_id))

    def _make_msg_handler(self, room_id: str):
        def handler(rid: str, message: Any) -> None:
            bridge = self.bridge_manager.lookup(rid)
            if bridge is None or not bridge.is_bound:
                return
            # Skip if the message @-mentions a non-harness persona; persona-manager
            # will handle it.
            mentions = getattr(message, "mentions", None) or []
            pm = self.persona_managers.get(rid)
            if pm is not None and any(m in pm.personas for m in mentions):
                return
            # Schedule dispatch
            import asyncio
            asyncio.create_task(bridge.dispatch_message(message))
        return handler
```

> The `router` and the `persona_managers` dict aren't captured at construction
> time on the real router because `_on_chat_init` is called after `attach()`;
> the closure captures via `self`. We pass `router` only to `attach`. The fix:
> store router on self in attach.

Update `attach`:

```python
def attach(self, router: Any) -> None:
    self.router = router
    router.observe_chat_init(self._on_chat_init)
```

And use `self.router.observe_chat_msg(...)` in `_on_chat_init`.

- [ ] **Step 4: Verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "add BridgeRouterIntegration: chat-init + chat-msg observers"
```

### Task 5.2: Suppress persona-manager default-persona fallback for bound chats

When a chat is bound to a harness, the per-chat `PersonaManager` should not auto-dispatch unmentioned messages to its default persona. Mutate the trait per-instance.

**Files:** Modify `router_integration.py`, extend tests

- [ ] **Step 1: Write the test**

```python
class _FakePersonaManager:
    def __init__(self):
        self.default_persona_id = "jupyternaut-id"
        self.personas = {"jupyternaut-id": object()}


def test_binding_suppresses_default_persona():
    pm = _FakePersonaManager()
    integration = BridgeRouterIntegration(
        registry=HarnessRegistry(),
        bridge_manager=BridgeManager(),
        persona_managers={"chat-1": pm},
    )
    adapter = HarnessAdapter(
        id="claude-code", display_name="x", icon="x.svg",
        executable_factory=lambda: ["x"],
    )
    integration.registry.register(adapter)
    bridge = integration.bridge_manager.get_or_create("chat-1")
    integration.bind_chat("chat-1", "claude-code")
    assert bridge.is_bound
    assert pm.default_persona_id is None or pm.default_persona_id == ""
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Add `bind_chat` method to integration**

```python
def bind_chat(self, room_id: str, harness_id: str) -> None:
    adapter = self.registry.get(harness_id)
    bridge = self.bridge_manager.get_or_create(room_id)
    bridge.bind(adapter)
    pm = self.persona_managers.get(room_id)
    if pm is not None:
        # Prevent default-persona auto-reply now that bridge handles dispatch.
        pm.default_persona_id = None
```

Refactor `BindHandler` to call `integration.bind_chat()` instead of the bridge directly. Update `extension.py` to pass `integration` to handlers.

- [ ] **Step 4: Verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "suppress default persona fallback when chat binds to harness"
```

### Task 5.3: Discover the persona-managers dict at runtime

`jupyter-ai-persona-manager` stores per-chat managers in
`serverapp.web_app.settings["jupyter-ai"]["persona-managers"]`. Wire up access from `extension.py`.

**Files:** Modify `extension.py`

- [ ] **Step 1: Update `initialize_settings`**

```python
async def _setup_router_integration(self) -> None:
    """Wait for router and persona-managers, then attach."""
    while True:
        router = self.serverapp.web_app.settings.get("jupyter-ai", {}).get("router")
        persona_managers = self.serverapp.web_app.settings.get(
            "jupyter-ai", {}
        ).get("persona-managers")
        if router is not None and persona_managers is not None:
            break
        import asyncio
        await asyncio.sleep(0.1)

    from .router_integration import BridgeRouterIntegration
    self.integration = BridgeRouterIntegration(
        registry=self.registry,
        bridge_manager=self.bridge_manager,
        persona_managers=persona_managers,
    )
    self.integration.attach(router)
    self.log.info("ACP bridge attached to router.")


def initialize_settings(self) -> None:
    # ... existing code ...
    from asyncio import get_event_loop_policy
    loop = get_event_loop_policy().get_event_loop()
    loop.create_task(self._setup_router_integration())
```

Update handler initialization to pass `self.integration` for `BindHandler`.

- [ ] **Step 2: Smoke-test by starting server**

```bash
jupyter server --no-browser &
sleep 5
jupyter server --no-browser stop || true
# Inspect logs for "ACP bridge attached to router."
```

- [ ] **Step 3: Commit**

```bash
git commit -am "wire router integration into extension lifecycle"
```

---

## Phase 6 — Claude Code adapter

Wraps `ClaudeCodeAcpPersona` (from `jupyter_ai_acp_client`) as the PoC harness. Adds the capability methods (`get_session_state`, `set_session_model`, etc.) on the wrapper subclass, which delegate to the underlying `JaiAcpClient`.

### Task 6.1: Write the adapter module

**Files:** Create `harnesses/claude_code.py`, `harnesses/__init__.py`, `tests/test_claude_code_adapter.py`

- [ ] **Step 1: Inspect the existing `ClaudeCodeAcpPersona` to learn how it's constructed**

```bash
gh api repos/jupyter-ai-contrib/jupyter-ai-acp-client/contents/jupyter_ai_acp_client/acp_personas/claude.py --jq '.content' | base64 -d | head -80
```

Read this output to determine:
- Default executable list (likely `["npx", "@zed-industries/claude-code-acp"]` or similar)
- Whether the class needs any kwargs beyond `parent`, `ychat`, `executable`
- What attributes/methods exist on the class

- [ ] **Step 2: Write the adapter**

`harnesses/claude_code.py`:

```python
"""Claude Code harness adapter."""
from __future__ import annotations

from jupyter_ai_acp_client.acp_personas.claude import (
    ClaudeCodePersona as _ClaudeCodePersona,
)

from ..adapter import HarnessAdapter
from ..registry import HarnessRegistry


class ClaudeCodeBridgePersona(_ClaudeCodePersona):
    """Bridge-side wrapper that adds capability methods.

    The base ClaudeCodePersona handles subprocess, session, slash-command
    capture. We add session-config setters that hit the underlying client.
    """

    async def get_session_state(self) -> dict:
        client = await self.get_client()
        session = await self.get_session_response()
        return {
            "selected_model_id": getattr(session, "selected_model_id", None),
            "available_models": [
                {"id": m.id, "name": m.name}
                for m in getattr(session, "available_models", []) or []
            ],
            "selected_mode_id": getattr(session, "selected_mode_id", None),
            "session_modes": [
                {"id": m.id, "name": m.name}
                for m in getattr(session, "session_modes", []) or []
            ],
            "config_options": [
                {"id": o.id, "name": o.name, "value": o.value}
                for o in getattr(session, "config_options", []) or []
            ],
            "available_commands": [
                {"name": c.name, "description": getattr(c, "description", "")}
                for c in getattr(self, "_acp_slash_commands", []) or []
            ],
        }

    async def set_session_model(self, model_id: str) -> None:
        client = await self.get_client()
        session_id = await self.get_session_id()
        await client.set_session_model(session_id=session_id, model_id=model_id)

    async def set_session_mode(self, mode_id: str) -> None:
        client = await self.get_client()
        session_id = await self.get_session_id()
        await client.set_session_mode(session_id=session_id, mode_id=mode_id)

    async def set_session_config_option(self, option_id: str, value) -> None:
        client = await self.get_client()
        session_id = await self.get_session_id()
        await client.set_session_config_option(
            session_id=session_id, option_id=option_id, value=value
        )


def _executable_factory() -> list[str]:
    return ["npx", "@zed-industries/claude-code-acp"]


CLAUDE_CODE = HarnessAdapter(
    id="claude-code",
    display_name="Claude Code",
    icon="claude-code.svg",
    executable_factory=_executable_factory,
    persona_class=ClaudeCodeBridgePersona,
)


def register(registry: HarnessRegistry) -> None:
    registry.register(CLAUDE_CODE)
```

> **Note:** The exact executable command and the ACP client method names
> (`set_session_model`, `set_session_mode`, `set_session_config_option`) need
> verification against `jupyter_ai_acp_client`'s `JaiAcpClient` implementation
> at the time of execution. If those methods don't exist, file a small upstream
> issue and add a thin shim that constructs the ACP request directly using
> the `acp` Python package's request types.

- [ ] **Step 3: Smoke test the adapter is importable**

```python
# tests/test_claude_code_adapter.py
def test_adapter_registered():
    from jupyter_ai_acp_bridge.harnesses.claude_code import CLAUDE_CODE
    assert CLAUDE_CODE.id == "claude-code"
    assert CLAUDE_CODE.persona_class is not None
    assert CLAUDE_CODE.executable_factory()[0] in ("npx", "claude-code-acp")
```

```bash
pytest jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_claude_code_adapter.py -v
```

- [ ] **Step 4: Commit**

```bash
git add jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/harnesses/__init__.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/harnesses/claude_code.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_claude_code_adapter.py
git commit -m "add Claude Code harness adapter"
```

### Task 6.2: End-to-end Python smoke test

Boots a Jupyter server with the bridge installed, binds chat-1 to claude-code via REST, queries state, sets model.

**Files:** `tests/test_smoke.py`

- [ ] **Step 1: Write the smoke test**

```python
import json
import subprocess
import time

import pytest
import requests


@pytest.mark.integration
def test_bridge_smoke():
    proc = subprocess.Popen(
        ["jupyter", "server", "--no-browser", "--port=18888",
         "--ServerApp.token=test", "--ServerApp.disable_check_xsrf=True"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        time.sleep(5)
        base = "http://localhost:18888/jupyter-ai-acp-bridge"
        headers = {"Authorization": "token test"}
        r = requests.get(f"{base}/harnesses", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert any(h["id"] == "claude-code" for h in body["harnesses"])
    finally:
        proc.terminate()
        proc.wait(timeout=10)
```

- [ ] **Step 2: Run** (skip if `claude-code-acp` not installed; the `harnesses` route doesn't need it)

```bash
pytest jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_smoke.py -v -m integration
```

Expected: passes; `claude-code` appears in registry.

- [ ] **Step 3: Commit**

```bash
git commit -am "add end-to-end smoke test"
```

---

## Phase 7 — TS API client + types

Mirrors the REST routes; consumed by all UI components.

### Task 7.1: TS types

**Files:** Create `src/types.ts`

- [ ] **Step 1: Write `src/types.ts`**

```typescript
export interface HarnessInfo {
  id: string;
  display_name: string;
  icon: string;
}

export interface ModelInfo {
  id: string;
  name: string;
}

export interface SessionMode {
  id: string;
  name: string;
}

export interface ConfigOption {
  id: string;
  name: string;
  value: unknown;
}

export interface AvailableCommand {
  name: string;
  description: string;
}

export interface ChatBridgeState {
  harness_id: string | null;
  selected_model_id?: string;
  available_models?: ModelInfo[];
  selected_mode_id?: string;
  session_modes?: SessionMode[];
  config_options?: ConfigOption[];
  available_commands?: AvailableCommand[];
}
```

- [ ] **Step 2: Commit**

```bash
git add jupyter-ai-acp-bridge/src/types.ts
git commit -m "add TS types for bridge state"
```

### Task 7.2: API client

**Files:** Create `src/api.ts`

- [ ] **Step 1: Write the test (jest)**

`src/__tests__/api.test.ts`:

```typescript
jest.mock('@jupyterlab/services', () => ({
  ServerConnection: {
    makeSettings: () => ({ baseUrl: 'http://localhost:8888/' }),
    makeRequest: jest.fn()
  }
}));
jest.mock('@jupyterlab/coreutils', () => ({
  URLExt: { join: (...parts: string[]) => parts.join('/').replace(/\/+/g, '/') }
}));

import { ServerConnection } from '@jupyterlab/services';
import {
  listHarnesses,
  bindHarness,
  getState,
  setModel,
  listCommands
} from '../api';

const makeRequest = ServerConnection.makeRequest as jest.Mock;

beforeEach(() => makeRequest.mockReset());

function mockResponse(body: unknown, ok = true) {
  makeRequest.mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    json: async () => body
  });
}

test('listHarnesses returns harnesses from response', async () => {
  mockResponse({ harnesses: [{ id: 'x', display_name: 'X', icon: 'x.svg' }] });
  const result = await listHarnesses();
  expect(result).toEqual([{ id: 'x', display_name: 'X', icon: 'x.svg' }]);
  expect(makeRequest).toHaveBeenCalledWith(
    expect.stringContaining('/jupyter-ai-acp-bridge/harnesses'),
    expect.any(Object),
    expect.any(Object)
  );
});

test('bindHarness POSTs harness_id', async () => {
  mockResponse({ harness_id: 'claude-code' });
  await bindHarness('chat-1', 'claude-code');
  const callArgs = makeRequest.mock.calls[0];
  expect(callArgs[0]).toContain('/chats/chat-1/bind');
  expect(callArgs[1].method).toBe('POST');
  expect(JSON.parse(callArgs[1].body)).toEqual({ harness_id: 'claude-code' });
});

test('getState returns state', async () => {
  mockResponse({ harness_id: 'claude-code', selected_model_id: 'sonnet' });
  const state = await getState('chat-1');
  expect(state.harness_id).toBe('claude-code');
});

test('setModel POSTs model_id', async () => {
  mockResponse({ ok: true });
  await setModel('chat-1', 'opus-4');
  const body = JSON.parse(makeRequest.mock.calls[0][1].body);
  expect(body).toEqual({ model_id: 'opus-4' });
});

test('listCommands returns commands array', async () => {
  mockResponse({ commands: [{ name: '/help', description: 'help' }] });
  const cmds = await listCommands('chat-1');
  expect(cmds).toEqual([{ name: '/help', description: 'help' }]);
});

test('non-OK response throws', async () => {
  mockResponse({ error: 'no' }, false);
  await expect(listHarnesses()).rejects.toThrow();
});
```

- [ ] **Step 2: Implement `src/api.ts`**

```typescript
import { ServerConnection } from '@jupyterlab/services';
import { URLExt } from '@jupyterlab/coreutils';
import {
  HarnessInfo,
  ChatBridgeState,
  AvailableCommand
} from './types';

const NAMESPACE = 'jupyter-ai-acp-bridge';

function url(path: string): string {
  const settings = ServerConnection.makeSettings();
  return URLExt.join(settings.baseUrl, NAMESPACE, path);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const settings = ServerConnection.makeSettings();
  const response = await ServerConnection.makeRequest(
    url(path),
    init ?? {},
    settings
  );
  if (!response.ok) {
    throw new Error(`Bridge request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function listHarnesses(): Promise<HarnessInfo[]> {
  const data = await request<{ harnesses: HarnessInfo[] }>('harnesses');
  return data.harnesses;
}

export async function bindHarness(
  chatId: string,
  harnessId: string
): Promise<{ harness_id: string }> {
  return request(`chats/${chatId}/bind`, {
    method: 'POST',
    body: JSON.stringify({ harness_id: harnessId })
  });
}

export async function getState(chatId: string): Promise<ChatBridgeState> {
  return request<ChatBridgeState>(`chats/${chatId}/state`);
}

export async function setModel(
  chatId: string,
  modelId: string
): Promise<void> {
  await request(`chats/${chatId}/model`, {
    method: 'POST',
    body: JSON.stringify({ model_id: modelId })
  });
}

export async function setMode(chatId: string, modeId: string): Promise<void> {
  await request(`chats/${chatId}/mode`, {
    method: 'POST',
    body: JSON.stringify({ mode_id: modeId })
  });
}

export async function setConfigOption(
  chatId: string,
  optionId: string,
  value: unknown
): Promise<void> {
  await request(`chats/${chatId}/config-option`, {
    method: 'POST',
    body: JSON.stringify({ option_id: optionId, value })
  });
}

export async function listCommands(
  chatId: string
): Promise<AvailableCommand[]> {
  const data = await request<{ commands: AvailableCommand[] }>(
    `chats/${chatId}/available-commands`
  );
  return data.commands;
}
```

- [ ] **Step 3: Verify build + test**

```bash
cd jupyter-ai-acp-bridge
jlpm build
jlpm test
```

- [ ] **Step 4: Commit**

```bash
git add jupyter-ai-acp-bridge/src/api.ts \
        jupyter-ai-acp-bridge/src/__tests__/api.test.ts
git commit -m "add TS API client"
```

---

## Phase 8 — TS picker + badge

Two components: a picker shown in draft state and a badge shown after binding.

### Task 8.1: `HarnessPicker` component

**Files:** Create `src/components/HarnessPicker.tsx`

- [ ] **Step 1: Write the component**

```tsx
import * as React from 'react';
import { useEffect, useState } from 'react';

import { HarnessInfo } from '../types';
import { listHarnesses, bindHarness } from '../api';

export interface HarnessPickerProps {
  chatId: string;
  onBound: (harnessId: string) => void;
}

export const HarnessPicker: React.FC<HarnessPickerProps> = ({
  chatId,
  onBound
}) => {
  const [harnesses, setHarnesses] = useState<HarnessInfo[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listHarnesses().then(setHarnesses).catch(console.error);
  }, []);

  const handlePick = async (id: string) => {
    setBusy(true);
    try {
      await bindHarness(chatId, id);
      onBound(id);
    } finally {
      setBusy(false);
    }
  };

  if (harnesses.length === 0) {
    return <div className="jp-acp-bridge-picker-empty">Loading agents…</div>;
  }

  return (
    <div className="jp-acp-bridge-picker">
      <span>Choose an agent:</span>
      {harnesses.map(h => (
        <button
          key={h.id}
          disabled={busy}
          onClick={() => handlePick(h.id)}
        >
          {h.display_name}
        </button>
      ))}
    </div>
  );
};
```

- [ ] **Step 2: Add a basic test**

```tsx
import { render, screen } from '@testing-library/react';
import * as React from 'react';
import { HarnessPicker } from '../components/HarnessPicker';

jest.mock('../api', () => ({
  listHarnesses: jest.fn().mockResolvedValue([
    { id: 'claude-code', display_name: 'Claude Code', icon: 'x.svg' }
  ]),
  bindHarness: jest.fn()
}));

test('renders harness buttons', async () => {
  render(<HarnessPicker chatId="chat-1" onBound={() => {}} />);
  expect(await screen.findByText('Claude Code')).toBeInTheDocument();
});
```

- [ ] **Step 3: Verify build**

```bash
jlpm build && jlpm test
```

- [ ] **Step 4: Commit**

```bash
git commit -am "add HarnessPicker component"
```

### Task 8.2: `HarnessBadge` component

**Files:** Create `src/components/HarnessBadge.tsx`

- [ ] **Step 1: Write component**

```tsx
import * as React from 'react';
import { HarnessInfo } from '../types';

export interface HarnessBadgeProps {
  harness: HarnessInfo;
}

export const HarnessBadge: React.FC<HarnessBadgeProps> = ({ harness }) => (
  <div className="jp-acp-bridge-badge" title={harness.display_name}>
    <img src={harness.icon} width={16} height={16} alt="" />
    <span>{harness.display_name}</span>
  </div>
);
```

- [ ] **Step 2: Commit**

```bash
git add jupyter-ai-acp-bridge/src/components/HarnessBadge.tsx
git commit -m "add HarnessBadge component"
```

### Task 8.3: Wire picker + badge into a chat-panel container

**Files:** Create `src/components/HarnessHeader.tsx`, update `src/index.ts`

- [ ] **Step 1: Write the container**

```tsx
import * as React from 'react';
import { useEffect, useState } from 'react';

import { HarnessInfo, ChatBridgeState } from '../types';
import { getState, listHarnesses } from '../api';
import { HarnessPicker } from './HarnessPicker';
import { HarnessBadge } from './HarnessBadge';

export const HarnessHeader: React.FC<{ chatId: string }> = ({ chatId }) => {
  const [state, setState] = useState<ChatBridgeState | null>(null);
  const [harnesses, setHarnesses] = useState<HarnessInfo[]>([]);

  useEffect(() => {
    Promise.all([getState(chatId), listHarnesses()]).then(([s, h]) => {
      setState(s);
      setHarnesses(h);
    });
  }, [chatId]);

  if (state === null) {
    return null;
  }
  if (state.harness_id === null) {
    return (
      <HarnessPicker
        chatId={chatId}
        onBound={id => setState({ harness_id: id })}
      />
    );
  }
  const matched = harnesses.find(h => h.id === state.harness_id);
  return matched ? <HarnessBadge harness={matched} /> : null;
};
```

- [ ] **Step 2: Plug into JupyterLab**

Update `src/index.ts` to register the `HarnessHeader` via `IInputToolbarRegistryFactory`. Read the existing acp-client `src/index.ts` again for the exact registration pattern and adapt:

```typescript
import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { IInputToolbarRegistryFactory } from '@jupyter/chat';
// HarnessHeader registration goes here once the right hook is identified.
```

> **Implementation note:** at the time the executor opens this file, verify
> the exact extension point. `@jupyter/chat` may use a different token name in
> the version pinned by the dev environment. If `IInputToolbarRegistryFactory`
> is not the right hook for "header above message log" (which is what we want
> for the picker/badge), use whichever extension point the package exposes for
> "above-input region" or "header region." If no such hook exists, fall back
> to placing the header inside the input toolbar (less ideal, more visible).

- [ ] **Step 3: Build, install lab extension, manually open a chat**

```bash
cd jupyter-ai-acp-bridge && jlpm build
jupyter lab --no-browser
```

Open a chat; expect to see "Choose an agent: [Claude Code]" button.

- [ ] **Step 4: Commit**

```bash
git commit -am "render HarnessHeader at top of chat panel"
```

---

## Phase 9 — TS selectors

Three small popover components for model / mode / config-options. Each polls `getState(chatId)` and shows nothing if its capability isn't advertised.

### Task 9.1: `ModelSelector`

**Files:** Create `src/components/ModelSelector.tsx`

- [ ] **Step 1: Write component**

```tsx
import * as React from 'react';
import { useEffect, useState } from 'react';
import { ChatBridgeState, ModelInfo } from '../types';
import { getState, setModel } from '../api';

export const ModelSelector: React.FC<{ chatId: string }> = ({ chatId }) => {
  const [state, setStateLocal] = useState<ChatBridgeState | null>(null);
  useEffect(() => {
    getState(chatId).then(setStateLocal);
  }, [chatId]);
  if (!state || !state.available_models || state.available_models.length === 0) {
    return null;
  }
  return (
    <select
      value={state.selected_model_id ?? ''}
      onChange={async e => {
        await setModel(chatId, e.target.value);
        setStateLocal({ ...state, selected_model_id: e.target.value });
      }}
      title="Model"
      className="jp-acp-bridge-model-selector"
    >
      {state.available_models.map((m: ModelInfo) => (
        <option key={m.id} value={m.id}>{m.name}</option>
      ))}
    </select>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add jupyter-ai-acp-bridge/src/components/ModelSelector.tsx
git commit -m "add ModelSelector component"
```

### Task 9.2: `ModeSelector`

**Files:** Create `src/components/ModeSelector.tsx`

- [ ] **Step 1: Write component (analogous to ModelSelector)**

```tsx
import * as React from 'react';
import { useEffect, useState } from 'react';
import { ChatBridgeState, SessionMode } from '../types';
import { getState, setMode } from '../api';

export const ModeSelector: React.FC<{ chatId: string }> = ({ chatId }) => {
  const [state, setStateLocal] = useState<ChatBridgeState | null>(null);
  useEffect(() => { getState(chatId).then(setStateLocal); }, [chatId]);
  if (!state || !state.session_modes || state.session_modes.length === 0) {
    return null;
  }
  return (
    <select
      value={state.selected_mode_id ?? ''}
      onChange={async e => {
        await setMode(chatId, e.target.value);
        setStateLocal({ ...state, selected_mode_id: e.target.value });
      }}
      title="Mode"
      className="jp-acp-bridge-mode-selector"
    >
      {state.session_modes.map((m: SessionMode) => (
        <option key={m.id} value={m.id}>{m.name}</option>
      ))}
    </select>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add jupyter-ai-acp-bridge/src/components/ModeSelector.tsx
git commit -m "add ModeSelector component"
```

### Task 9.3: `ConfigOptionsSelector`

**Files:** Create `src/components/ConfigOptionsSelector.tsx`

- [ ] **Step 1: Write component**

```tsx
import * as React from 'react';
import { useEffect, useState } from 'react';
import { ChatBridgeState, ConfigOption } from '../types';
import { getState, setConfigOption } from '../api';

export const ConfigOptionsSelector: React.FC<{ chatId: string }> = ({
  chatId
}) => {
  const [state, setStateLocal] = useState<ChatBridgeState | null>(null);
  useEffect(() => { getState(chatId).then(setStateLocal); }, [chatId]);
  if (!state || !state.config_options || state.config_options.length === 0) {
    return null;
  }
  return (
    <details className="jp-acp-bridge-config-options">
      <summary>Options</summary>
      {state.config_options.map((o: ConfigOption) => (
        <label key={o.id}>
          {o.name}
          <input
            type="text"
            defaultValue={String(o.value ?? '')}
            onBlur={e => setConfigOption(chatId, o.id, e.target.value)}
          />
        </label>
      ))}
    </details>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add jupyter-ai-acp-bridge/src/components/ConfigOptionsSelector.tsx
git commit -m "add ConfigOptionsSelector component"
```

### Task 9.4: Plug selectors into the input toolbar

**Files:** Modify `src/index.ts`

- [ ] **Step 1: Register selectors via `IInputToolbarRegistryFactory`**

This requires running with `jupyterlab_chat` and inspecting the exact registry factory API. Refer to the acp-client's pattern (which uses `preambleRegistry.addComponent`). The bridge's selectors should live in the input toolbar; the registry factory pattern accepts a function `(chatContext) => Component`.

```typescript
import { IInputToolbarRegistryFactory } from '@jupyter/chat';
import { ModelSelector } from './components/ModelSelector';
import { ModeSelector } from './components/ModeSelector';
import { ConfigOptionsSelector } from './components/ConfigOptionsSelector';

export const selectorsPlugin: JupyterFrontEndPlugin<void> = {
  id: '@jupyter-ai/acp-bridge:selectors',
  autoStart: true,
  requires: [IInputToolbarRegistryFactory],
  activate: (app, factory: IInputToolbarRegistryFactory) => {
    factory.addItem(ctx => <ModelSelector chatId={ctx.chatId} />);
    factory.addItem(ctx => <ModeSelector chatId={ctx.chatId} />);
    factory.addItem(ctx => <ConfigOptionsSelector chatId={ctx.chatId} />);
  }
};

export default [plugin, selectorsPlugin];
```

> **Implementation note:** the exact `IInputToolbarRegistryFactory` API may
> differ. The executor should `gh api repos/jupyterlab/jupyter-chat/contents/packages/jupyter-chat/src/tokens.ts`
> at execution time to confirm the method names. The pattern is right; the
> name might be `addProvider`, `register`, etc.

- [ ] **Step 2: Build and test in lab**

```bash
jlpm build && jupyter lab --no-browser
```

Open a chat bound to claude-code and verify the dropdowns appear in the input toolbar.

- [ ] **Step 3: Commit**

```bash
git commit -am "register selectors via input toolbar registry"
```

---

## Phase 10 — Slash + mention completion

Adopt the acp-client's `IChatCommandProvider` pattern with a bridge-specific endpoint.

### Task 10.1: `BridgeSlashCommandProvider`

**Files:** Create `src/providers/BridgeSlashCommandProvider.ts`

- [ ] **Step 1: Write the provider** (modeled directly on acp-client/src/index.ts SlashCommandProvider)

```typescript
import {
  IChatCommandProvider,
  IInputModel,
  ChatCommand
} from '@jupyter/chat';

import { listCommands } from '../api';

const PROVIDER_ID = '@jupyter-ai/acp-bridge:slash-command-provider';

export class BridgeSlashCommandProvider implements IChatCommandProvider {
  public id = PROVIDER_ID;
  _regex = /\/([\w-]*)/g;

  async listCommandCompletions(
    inputModel: IInputModel
  ): Promise<ChatCommand[]> {
    const word = inputModel.currentWord || '';
    if (!word.startsWith('/')) {
      return [];
    }
    if (!inputModel.chatContext) {
      return [];
    }
    const chatId = inputModel.chatContext.name;
    const commands = await listCommands(chatId);
    return commands
      .filter(c => c.name.startsWith(word))
      .map(c => ({
        name: c.name,
        providerId: this.id,
        description: c.description,
        spaceOnAccept: true
      }));
  }

  async onSubmit(): Promise<void> {
    return;
  }
}
```

- [ ] **Step 2: Register in `src/index.ts`**

```typescript
import { IChatCommandRegistry } from '@jupyter/chat';
import { BridgeSlashCommandProvider } from './providers/BridgeSlashCommandProvider';

export const slashPlugin: JupyterFrontEndPlugin<void> = {
  id: '@jupyter-ai/acp-bridge:slash',
  autoStart: true,
  requires: [IChatCommandRegistry],
  activate: (app, registry: IChatCommandRegistry) => {
    registry.addProvider(new BridgeSlashCommandProvider());
  }
};

// add slashPlugin to default export array
```

- [ ] **Step 3: Commit**

```bash
git add jupyter-ai-acp-bridge/src/providers/BridgeSlashCommandProvider.ts
git commit -am "add BridgeSlashCommandProvider"
```

### Task 10.2: `@`-mention completion for Jupyter resources

For PoC, support `@<filename>` matching files in workspace. Persona-name `@`-mentions are already handled by jupyterlab_chat's existing persona-mention provider, so we don't need to add anything for them.

**Files:** Create `src/providers/BridgeMentionProvider.ts`

- [ ] **Step 1: Write minimal provider**

```typescript
import {
  IChatCommandProvider,
  IInputModel,
  ChatCommand
} from '@jupyter/chat';
import { Contents } from '@jupyterlab/services';

const PROVIDER_ID = '@jupyter-ai/acp-bridge:mention-provider';

export class BridgeMentionProvider implements IChatCommandProvider {
  public id = PROVIDER_ID;
  _regex = /@([\w./-]*)/g;

  constructor(private contents: Contents.IManager) {}

  async listCommandCompletions(
    inputModel: IInputModel
  ): Promise<ChatCommand[]> {
    const word = inputModel.currentWord || '';
    if (!word.startsWith('@')) {
      return [];
    }
    const fragment = word.slice(1);
    if (!fragment) return [];
    try {
      const listing = await this.contents.get('', { content: true });
      if (!listing.content) return [];
      const items = (listing.content as Contents.IModel[])
        .filter(m => m.name.startsWith(fragment))
        .slice(0, 10);
      return items.map(m => ({
        name: `@${m.name}`,
        providerId: this.id,
        description: m.path,
        spaceOnAccept: true
      }));
    } catch {
      return [];
    }
  }

  async onSubmit(): Promise<void> {
    return;
  }
}
```

- [ ] **Step 2: Register in `src/index.ts`** (require `Contents` token from `@jupyterlab/services` or use `app.serviceManager.contents`):

```typescript
import { BridgeMentionProvider } from './providers/BridgeMentionProvider';

export const mentionPlugin: JupyterFrontEndPlugin<void> = {
  id: '@jupyter-ai/acp-bridge:mention',
  autoStart: true,
  requires: [IChatCommandRegistry],
  activate: (app, registry: IChatCommandRegistry) => {
    registry.addProvider(new BridgeMentionProvider(app.serviceManager.contents));
  }
};
```

- [ ] **Step 3: Commit**

```bash
git add jupyter-ai-acp-bridge/src/providers/BridgeMentionProvider.ts
git commit -am "add BridgeMentionProvider for @<filename>"
```

> **Note:** Per the spec, `@`-mentions should resolve to typed ACP content
> blocks. The PoC sends them as inline text and lets the harness parse `@file`
> natively (which Claude Code does). Typed-content-block resolution at send
> time is a follow-up — file an issue and document in §11 of the spec.

---

## Phase 11 — Integration test with fake ACP agent

Spawn a fake ACP agent that advertises configurable capabilities; verify selector visibility responds.

### Task 11.1: Build the fake ACP agent

**Files:** Create `tests/fake_acp_agent.py`

- [ ] **Step 1: Write a minimal stdio ACP server**

```python
"""Fake ACP agent for integration tests.

Speaks the ACP JSON-RPC protocol over stdio. Advertises a configurable
capability set so the bridge UI can be tested.

Usage: python -m jupyter_ai_acp_bridge.tests.fake_acp_agent
"""
import asyncio
import json
import os
import sys


CAPABILITIES = {
    "available_models": [
        {"id": "fake-1", "name": "Fake One"},
        {"id": "fake-2", "name": "Fake Two"},
    ],
    "session_modes": [{"id": "default", "name": "Default"}],
    "available_commands": [{"name": "/help", "description": "Help"}],
}


async def main() -> None:
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    writer_transport, writer_protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, loop)

    while True:
        line = await reader.readline()
        if not line:
            break
        try:
            req = json.loads(line)
        except Exception:
            continue
        method = req.get("method")
        if method == "session/new":
            resp = {
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "result": {
                    "session_id": "fake-session",
                    "selected_model_id": "fake-1",
                    "available_models": CAPABILITIES["available_models"],
                    "session_modes": CAPABILITIES["session_modes"],
                    "selected_mode_id": "default",
                },
            }
        else:
            resp = {"jsonrpc": "2.0", "id": req.get("id"), "result": {}}
        writer.write((json.dumps(resp) + "\n").encode("utf-8"))
        await writer.drain()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Add a fake harness adapter**

`harnesses/fake.py`:

```python
"""Fake harness adapter for integration tests."""
import sys

from jupyter_ai_acp_client.base_acp_persona import BaseAcpPersona

from ..adapter import HarnessAdapter
from ..registry import HarnessRegistry


class FakePersona(BaseAcpPersona):
    pass


def _exec_factory():
    return [sys.executable, "-m", "jupyter_ai_acp_bridge.tests.fake_acp_agent"]


FAKE = HarnessAdapter(
    id="fake",
    display_name="Fake Agent",
    icon="fake.svg",
    executable_factory=_exec_factory,
    persona_class=FakePersona,
)


def register(registry: HarnessRegistry) -> None:
    registry.register(FAKE)
```

- [ ] **Step 3: Commit**

```bash
git add jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/fake_acp_agent.py \
        jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/harnesses/fake.py
git commit -m "add fake ACP agent + harness for integration tests"
```

### Task 11.2: Capability-driven selector visibility test

**Files:** Create `tests/test_integration_capability.py`

- [ ] **Step 1: Write the integration test**

```python
import asyncio

import pytest

from jupyter_ai_acp_bridge.harnesses.fake import FAKE
from jupyter_ai_acp_bridge.bridge import ChatBridge


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fake_agent_advertises_models():
    bridge = ChatBridge(chat_id="test-chat")
    bridge.bind(FAKE, parent=object())
    # Wait for session to come up
    await asyncio.sleep(2)
    state = await bridge.get_state()
    assert state["harness_id"] == "fake"
    assert any(m["id"] == "fake-1" for m in state["available_models"])
    assert any(m["id"] == "default" for m in state["session_modes"])
```

- [ ] **Step 2: Run** (this is the moment of truth for end-to-end wiring)

```bash
pytest jupyter-ai-acp-bridge/jupyter_ai_acp_bridge/tests/test_integration_capability.py -v -m integration
```

If it fails, check: (a) `BaseAcpPersona` constructor signature; (b) the fake agent's session/new response shape against what the ACP client expects; (c) any missing `parent` parameter.

- [ ] **Step 3: Commit**

```bash
git commit -am "add capability-driven integration test"
```

---

## Phase 12 — Metapackage wiring + docs

### Task 12.1: Add to metapackage `pyproject.toml`

**Files:** Modify `/home/cboettig/Documents/github/cboettig/jupyter-ai/pyproject.toml`

- [ ] **Step 1: Add the bridge as an optional dependency**

```toml
[project.optional-dependencies]
magics = [...]
jupyternaut = [...]
acp-bridge = ["jupyter_ai_acp_bridge>=0.0.1"]
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "expose acp-bridge as a metapackage extra"
```

### Task 12.2: User-facing docs

**Files:** Create `docs/source/users/acp-bridge.md`

- [ ] **Step 1: Write user docs**

```markdown
# ACP harness selector (preview)

The `jupyter-ai-acp-bridge` package adds a Zed-style per-thread harness
selector. Install it with:

```
pip install -e jupyter-ai-acp-bridge
```

Open a new chat: a harness picker appears at the top of the panel. Pick
"Claude Code" (or another harness) to bind the chat. After binding:

- All unmentioned messages go to the selected harness.
- The bottom toolbar shows model, mode, and config-option dropdowns when
  the harness advertises them.
- Slash commands (`/help`, `/permissions`, ...) auto-complete from the
  harness's advertised commands.
- `@<persona-name>` still routes to non-harness personas (e.g. jupyternaut)
  for one-off questions.
- `@<filename>` attaches a file by name.

Switching harness for a chat is not supported — start a new chat instead.
```

- [ ] **Step 2: Add link to user index**

Append to `docs/source/users/index.md`: a line linking to `acp-bridge.md`.

- [ ] **Step 3: Commit**

```bash
git add docs/source/users/acp-bridge.md docs/source/users/index.md
git commit -m "document ACP bridge for users"
```

### Task 12.3: Developer rationale doc

**Files:** Create `docs/source/developers/acp-bridge-rationale.md`

- [ ] **Step 1: Write rationale**

```markdown
# ACP bridge: why a separate package?

This package exists to demonstrate the design proposed in jupyter-ai
issue #1558: ACP harnesses should not be exposed as `@`-mentionable
personas. Instead, a chat thread binds to one harness for its life,
with toolbar selectors for model, mode, and config options driven by
ACP capabilities the harness advertises.

The bridge is purely additive: existing `acp_personas/*` registry
entries continue to work, jupyternaut and custom `BasePersona`
extensions are untouched. See the design spec at
`docs/superpowers/specs/2026-04-28-acp-bridge-design.md` and Zed's
analogous architecture at `crates/acp_thread/` and
`crates/agent_servers/` in the zed-industries/zed repository.
```

- [ ] **Step 2: Commit**

```bash
git add docs/source/developers/acp-bridge-rationale.md
git commit -m "add developer rationale for ACP bridge"
```

---

## Done criteria

When the following all pass, the PoC is ready to demo against issue #1558:

- `pytest jupyter-ai-acp-bridge` passes (unit + integration).
- `jlpm build && jlpm test` in `jupyter-ai-acp-bridge/` passes.
- `jupyter server extension list` shows `jupyter_ai_acp_bridge: OK`.
- `jupyter labextension list` shows `@jupyter-ai/acp-bridge`.
- Manual test in a real `jupyter lab` session:
  1. Open a new chat.
  2. Picker appears, "Claude Code" is selectable.
  3. Click it; identity badge replaces the picker.
  4. Send a message; Claude Code replies.
  5. Model dropdown shows live `available_models`; switching takes effect.
  6. Mode dropdown shows session modes; switching is respected.
  7. Typing `/help` completes against Claude Code's commands.
  8. Typing `@<filename>` completes against workspace files.
  9. Typing `@jupyternaut, hello` (with jupyternaut installed) routes to
     jupyternaut, not to Claude Code.
  10. Reload the page: chat reopens with binding intact.
  11. Attempt to bind a different harness via curl: returns 409.

---

## Self-review notes

- §3 of the spec is covered by Phases 1–6 (Python core).
- §4 (selector population: pure ACP capability-driven) is covered by Task 2.5
  (capability methods on bridge), Phase 6 (Claude Code adapter exposing them),
  and Phase 9 (selectors that hide when capability absent).
- §5 routing-rule augmentation is covered by Phase 5.
- §6 UI placement is covered by Phases 8–10. Note: the exact `@jupyter/chat`
  extension-point names are pinned as recommended but the executor may need
  to verify against the actual installed version.
- §7.1 (custom URI for cells) is implemented in Task 3.2; the spec marks this
  as a known mapping decision, not a risk.
- §7.2 (dual `@claude` visibility) is preserved: we don't remove any existing
  persona registrations.
- §7.3, §7.4, §7.5 (harnesses without `BaseAcpPersona`, default-reset
  semantics, slash-command edge cases) are documented but not addressed in
  the PoC; they're in the spec's out-of-scope list.
- Spec §8 testing strategy is covered by Phase 11 plus per-task pytest/jest
  tests.
- Spec §10 success criteria are reflected in the Done criteria above.

If executor finds a gap not on this list, file an issue rather than expanding
plan scope.
