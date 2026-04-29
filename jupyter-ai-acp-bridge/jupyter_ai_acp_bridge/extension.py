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

        # Schedule the integration setup once the event loop is running.
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.create_task(self._setup_router_integration())

        elapsed = round((time.time() - start) * 1000)
        self.log.info(f"Initialized {self.name} in {elapsed} ms.")

    async def _setup_router_integration(self) -> None:
        """Wait for jupyter-ai-router and jupyter-ai-persona-manager,
        then create + attach the integration."""
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

        # Update the BindHandler kwargs in-place so it can use the integration.
        # Tornado constructs handlers per request and reads kwargs at that time,
        # so mutating the dict here is picked up by all subsequent requests.
        self._bind_kwargs["integration"] = self.integration

        self.log.info("ACP bridge attached to router.")
