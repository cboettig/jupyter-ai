"""Jupyter Server extension entry point."""
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
