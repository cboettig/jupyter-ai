"""jupyter-ai-acp-bridge: per-thread ACP harness binding for Jupyter AI."""

__version__ = "0.0.1"


def _jupyter_server_extension_points():
    from jupyter_ai_acp_bridge.extension import AcpBridgeExtension

    return [{"module": "jupyter_ai_acp_bridge.extension", "app": AcpBridgeExtension}]
