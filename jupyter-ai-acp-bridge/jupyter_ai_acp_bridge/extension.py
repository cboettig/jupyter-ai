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
