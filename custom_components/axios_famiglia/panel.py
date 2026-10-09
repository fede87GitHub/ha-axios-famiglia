"""Pannello personalizzato nella barra laterale (frontend/axios-panel.js)."""
from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import slugify

from .const import CONF_STUDENT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "axios-famiglia"
PANEL_ELEMENT = "axios-famiglia-panel"
PANEL_TITLE = "Axios Famiglia"
PANEL_ICON = "mdi:school"
# True: il pannello lo vedono solo gli amministratori di Home Assistant.
# Con False (predefinito) lo vede ogni utente che ha accesso a Home Assistant.
PANEL_REQUIRE_ADMIN = False

FRONTEND_DIR = Path(__file__).parent / "frontend"
PANEL_FILE = "axios-panel.js"
STATIC_URL = f"/{DOMAIN}_static"
WS_STUDENTS = f"{DOMAIN}/students"

_STATE_KEY = f"{DOMAIN}_panel_state"


def _file_version() -> str:
    """Versione del file JavaScript (data di modifica): cambia a ogni aggiornamento,
    così il browser non usa una copia vecchia dalla cache."""
    try:
        return str(int((FRONTEND_DIR / PANEL_FILE).stat().st_mtime))
    except OSError:
        return "0"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Registra pannello, file statici e comando WebSocket (una sola volta)."""
    state = hass.data.setdefault(_STATE_KEY, {"ws": False, "static": False, "panel": False})

    if not state["ws"]:
        websocket_api.async_register_command(hass, ws_students)
        state["ws"] = True

    if not state["static"]:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), False)]
        )
        state["static"] = True

    if state["panel"]:
        return

    version = await hass.async_add_executor_job(_file_version)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{STATIC_URL}/{PANEL_FILE}?v={version}",
        require_admin=PANEL_REQUIRE_ADMIN,
        config={"version": version},
    )
    state["panel"] = True
    _LOGGER.debug("Axios: sidebar panel registered (v=%s)", version)


@callback
def async_remove_panel(hass: HomeAssistant) -> None:
    """Toglie il pannello dalla barra laterale (quando l'ultimo studente viene rimosso)."""
    state = hass.data.get(_STATE_KEY)
    if state and state["panel"]:
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
        state["panel"] = False


@websocket_api.websocket_command({vol.Required("type"): WS_STUDENTS})
@callback
def ws_students(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Elenco degli studenti configurati: il pannello costruisce da qui i nomi delle entità."""
    students = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        name = (entry.data.get(CONF_STUDENT_NAME) or "").strip()
        if name:
            students.append({"entry_id": entry.entry_id, "name": name, "slug": slugify(name)})
    connection.send_result(msg["id"], students)
