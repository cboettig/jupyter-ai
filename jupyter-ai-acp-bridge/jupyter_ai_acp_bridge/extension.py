"""Jupyter Server extension entry point."""
from __future__ import annotations

import asyncio
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
from .router_integration import BridgeRouterIntegration


URL = r"/jupyter-ai-acp-bridge"


class AcpBridgeExtension(ExtensionApp):
    name = "jupyter_ai_acp_bridge"
    handlers: list = []  # populated in initialize_settings

    registry: HarnessRegistry
    bridge_manager: BridgeManager
    integration: BridgeRouterIntegration | None

    def initialize_settings(self) -> None:
        start = time.time()
        self.registry = HarnessRegistry()

        # Register built-in harness adapters.
        from .harnesses.claude_code import register as register_claude_code
        register_claude_code(self.registry)

        self.bridge_manager = BridgeManager()
        self.integration = None  # set by _setup_router_integration

        # Make registry / manager available to other extensions
        if "jupyter-ai" not in self.settings:
            self.settings["jupyter-ai"] = {}
        self.settings["jupyter-ai"]["acp-bridge-registry"] = self.registry
        self.settings["jupyter-ai"]["acp-bridge-manager"] = self.bridge_manager

        bind_kwargs = {
            "registry": self.registry,
            "bridge_manager": self.bridge_manager,
            "integration": None,  # filled in once integration is ready (BindHandler reads from self.integration via initialize-time arg; for simplicity we mutate this dict)
        }
        common_kwargs = {
            "registry": self.registry,
            "bridge_manager": self.bridge_manager,
        }
        self._bind_kwargs = bind_kwargs
        self.handlers = [
            (URL + r"/harnesses", HarnessesHandler, common_kwargs),
            (URL + r"/chats/([^/]+)/bind", BindHandler, bind_kwargs),
            (URL + r"/chats/([^/]+)/state", StateHandler, common_kwargs),
            (URL + r"/chats/([^/]+)/model", ModelHandler, common_kwargs),
            (URL + r"/chats/([^/]+)/mode", ModeHandler, common_kwargs),
            (URL + r"/chats/([^/]+)/config-option", ConfigOptionHandler, common_kwargs),
            (URL + r"/chats/([^/]+)/available-commands", AvailableCommandsHandler, common_kwargs),
        ]

        # Schedule the integration setup. Jupyter Server's
        # `initialize_settings` runs before the Tornado IOLoop has entered its
        # run phase, so `asyncio.get_running_loop()` would raise here. We use
        # `get_event_loop_policy().get_event_loop()` instead — it returns the
        # loop Tornado is about to run, which is exactly the loop we want to
        # schedule on. Mirrors the pattern in `jupyter-ai-persona-manager`'s
        # extension. See PR/discussion linked from issue #1558.
        try:
            loop = asyncio.get_event_loop_policy().get_event_loop()
        except RuntimeError:
            self.log.warning(
                "ACP bridge: no event loop available at extension init; "
                "router integration will not be attached."
            )
        else:
            loop.create_task(self._setup_router_integration())

        elapsed = round((time.time() - start) * 1000)
        self.log.info(f"Initialized {self.name} in {elapsed} ms.")

    async def _setup_router_integration(self) -> None:
        """Wait for jupyter-ai-router and jupyter-ai-persona-manager,
        then create + attach the integration. Logs any exception that escapes."""
        try:
            while True:
                ja = self.serverapp.web_app.settings.get("jupyter-ai", {}) if self.serverapp else {}
                router = ja.get("router")
                persona_managers = ja.get("persona-managers")
                if router is not None and persona_managers is not None:
                    break
                await asyncio.sleep(0.1)

            self.integration = BridgeRouterIntegration(
                registry=self.registry,
                bridge_manager=self.bridge_manager,
                persona_managers=persona_managers,
            )
            self.integration.attach(router)

            # Inject the integration into BindHandler's kwargs by mutating
            # the dict in place. Tornado constructs handlers per request from
            # this same dict, so subsequent requests will see the new value.
            self._bind_kwargs["integration"] = self.integration

            self.log.info("ACP bridge attached to router.")
        except Exception:
            self.log.exception("ACP bridge integration setup failed.")
