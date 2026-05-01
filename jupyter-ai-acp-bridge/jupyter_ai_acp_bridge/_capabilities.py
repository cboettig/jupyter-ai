"""Real-ACP capability accessors shared by every bridge persona.

`BaseAcpPersona` already gives us a `JaiAcpClient` (`get_client`) and a
session response future (`get_session_response`); the ACP client connection
has direct `set_session_model` / `set_session_mode` / `set_config_option`
methods. This mixin just glues those together with our `/state` payload
shape so the bridge's `/state`, `/model`, `/mode`, `/config-option`
endpoints work uniformly across harnesses without each adapter
duplicating the plumbing.

Selected-model state is tracked on the persona instance (lazy attribute,
no `__init__` override needed) since `set_session_model` is fire-and-
forget — agents may not push a `SessionModelChanged` update outside of a
prompt cycle.
"""
from __future__ import annotations

from typing import Any


_MODEL_ATTR = "_acp_bridge_selected_model_id"
_MODE_ATTR = "_acp_bridge_selected_mode_id"
_LOGGED_RESPONSE_ATTR = "_acp_bridge_logged_response"


class AcpBridgeCapabilityMixin:
    async def get_session_state(self) -> dict:
        try:
            response = await self.get_session_response()  # type: ignore[attr-defined]
        except Exception:
            response = None

        # Temporary diagnostic (P2 Step 1, 2026-05-01): log the raw shape of
        # NewSessionResponse the FIRST time a chat asks for state, so we can
        # see whether claude-agent-acp / opencode actually populate
        # `models` / `modes` / `config_options`. Remove once UI is wired.
        if response is not None and not getattr(
            self, _LOGGED_RESPONSE_ATTR, False
        ):
            log = getattr(self, "log", None)
            if log is not None:
                try:
                    models = getattr(response, "models", None)
                    modes = getattr(response, "modes", None)
                    cfg = getattr(response, "config_options", None)
                    log.info(
                        "[acp-bridge diagnostic] persona=%s "
                        "session_response.models=%r "
                        "session_response.modes=%r "
                        "session_response.config_options=%r",
                        type(self).__name__,
                        models.model_dump(by_alias=True)
                        if models is not None
                        else None,
                        modes.model_dump(by_alias=True)
                        if modes is not None
                        else None,
                        [c.model_dump(by_alias=True) for c in cfg]
                        if cfg
                        else cfg,
                    )
                except Exception as exc:
                    log.warning(
                        "[acp-bridge diagnostic] failed to dump response: %r",
                        exc,
                    )
            setattr(self, _LOGGED_RESPONSE_ATTR, True)

        available_models: list[dict] = []
        selected_model_id = getattr(self, _MODEL_ATTR, None)
        session_modes: list[dict] = []
        selected_mode_id = getattr(self, _MODE_ATTR, None)
        config_options: list[dict] = []

        if response is not None:
            models_state = getattr(response, "models", None)
            if models_state is not None:
                for m in models_state.available_models or []:
                    available_models.append(
                        {
                            "id": m.model_id,
                            "name": m.name,
                            "description": getattr(m, "description", None),
                        }
                    )
                if selected_model_id is None:
                    selected_model_id = models_state.current_model_id

            modes_state = getattr(response, "modes", None)
            if modes_state is not None:
                for mode in modes_state.available_modes or []:
                    session_modes.append(
                        {
                            "id": mode.id,
                            "name": getattr(mode, "name", mode.id),
                            "description": getattr(mode, "description", None),
                        }
                    )
                if selected_mode_id is None:
                    selected_mode_id = modes_state.current_mode_id

            for opt in getattr(response, "config_options", None) or []:
                # ConfigOptions can be Boolean or Select — surface a flat
                # shape with `kind` so the frontend can render either.
                kind = getattr(opt, "type", None) or type(opt).__name__
                config_options.append(
                    {
                        "id": opt.id,
                        "name": getattr(opt, "name", opt.id),
                        "kind": kind,
                        "value": getattr(opt, "value", None),
                        "options": [
                            {"id": o.id, "name": getattr(o, "name", o.id)}
                            for o in getattr(opt, "options", None) or []
                        ],
                    }
                )

        return {
            "selected_model_id": selected_model_id,
            "available_models": available_models,
            "selected_mode_id": selected_mode_id,
            "session_modes": session_modes,
            "config_options": config_options,
            "available_commands": list(
                getattr(self, "_acp_slash_commands", []) or []
            ),
        }

    async def set_session_model(self, model_id: str) -> None:
        client = await self.get_client()  # type: ignore[attr-defined]
        conn = await client.get_connection()
        session_id = await self.get_session_id()  # type: ignore[attr-defined]
        await conn.set_session_model(model_id=model_id, session_id=session_id)
        # Track locally so the next `/state` reports the new selection
        # without needing the agent to emit a SessionUpdate.
        setattr(self, _MODEL_ATTR, model_id)

    async def set_session_mode(self, mode_id: str) -> None:
        client = await self.get_client()  # type: ignore[attr-defined]
        conn = await client.get_connection()
        session_id = await self.get_session_id()  # type: ignore[attr-defined]
        await conn.set_session_mode(mode_id=mode_id, session_id=session_id)
        setattr(self, _MODE_ATTR, mode_id)

    async def set_session_config_option(self, option_id: str, value: Any) -> None:
        client = await self.get_client()  # type: ignore[attr-defined]
        conn = await client.get_connection()
        session_id = await self.get_session_id()  # type: ignore[attr-defined]
        await conn.set_config_option(
            config_id=option_id, session_id=session_id, value=value
        )
