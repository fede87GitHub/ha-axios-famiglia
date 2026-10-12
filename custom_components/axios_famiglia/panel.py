"""Pannello personalizzato nella barra laterale (frontend/axios-panel.js)."""
from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import slugify

from .api import AxiosApiError, mark_as_read_allowed
from .const import CONF_STUDENT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "axios-famiglia"
PANEL_ELEMENT = "axios-famiglia-panel"
PANEL_TITLE = "Axios Famiglia"
PANEL_ICON = "mdi:school"
# True: il pannello lo vedono solo gli amministratori di Home Assistant, e solo loro possono
# aprire gli allegati delle comunicazioni.
# Con False (predefinito) lo vede ogni utente che ha accesso a Home Assistant.
PANEL_REQUIRE_ADMIN = False

FRONTEND_DIR = Path(__file__).parent / "frontend"
PANEL_FILE = "axios-panel.js"
STATIC_URL = f"/{DOMAIN}_static"
WS_STUDENTS = f"{DOMAIN}/students"
WS_ATTACHMENT = f"{DOMAIN}/attachment"
WS_CAPABILITIES = f"{DOMAIN}/capabilities"

_STATE_KEY = f"{DOMAIN}_panel_state"


def _file_version() -> str:
    """Versione del file JavaScript (data di modifica): cambia a ogni aggiornamento,
    così il browser non usa una copia vecchia dalla cache."""
    try:
        return str(int((FRONTEND_DIR / PANEL_FILE).stat().st_mtime))
    except OSError:
        return "0"


async def async_register_panel(hass: HomeAssistant) -> None:
    """Registra pannello, file statici e comandi WebSocket (una sola volta)."""
    state = hass.data.setdefault(_STATE_KEY, {"ws": False, "static": False, "panel": False})

    if not state["ws"]:
        websocket_api.async_register_command(hass, ws_students)
        websocket_api.async_register_command(hass, ws_attachment)
        websocket_api.async_register_command(hass, ws_capabilities)
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


@websocket_api.websocket_command({vol.Required("type"): WS_CAPABILITIES})
@callback
def ws_capabilities(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Cosa consente l'integrazione: il pannello lo usa per mostrare le impostazioni giuste."""
    connection.send_result(msg["id"], {"mark_as_read": mark_as_read_allowed()})


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_ATTACHMENT,
        vol.Required("entry_id"): str,
        vol.Required("post_id"): str,
        vol.Optional("attachment_id"): str,
        vol.Optional("mark_read"): bool,
    }
)
@websocket_api.async_response
async def ws_attachment(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Prepara l'apertura dell'allegato di una comunicazione.

    `mark_read` (facoltativo) e' la scelta fatta nelle impostazioni del pannello su quel dispositivo.
    La risposta e' {"status": "none"}, {"status": "choose", "attachments": [...]} oppure
    {"status": "ok", "url": ..., "name": ..., "marked_read": bool}: l'indirizzo e' temporaneo
    e va aperto subito, senza salvarlo.
    """
    if PANEL_REQUIRE_ADMIN and not connection.user.is_admin:
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Admin access required")
        return

    coordinator = (hass.data.get(DOMAIN) or {}).get(msg["entry_id"])
    client = getattr(coordinator, "client", None)
    if client is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Unknown student")
        return

    try:
        result = await client.async_open_attachment(
            msg["post_id"], msg.get("attachment_id"), msg.get("mark_read")
        )
    except ValueError:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, "Invalid communication id")
    except AxiosApiError as err:
        # Il messaggio dettagliato resta nei log; al pannello va un testo generico
        _LOGGER.warning("Axios: could not prepare the attachment: %s", err)
        connection.send_error(msg["id"], "portal_error", "The portal did not return the attachment")
    else:
        # Prima la risposta al pannello (la scheda del PDF e' in attesa), poi, in secondo piano,
        # un aggiornamento: se la comunicazione e' stata segnata come letta, i contatori delle
        # non lette si allineano subito invece che al prossimo giro (fino a 30 minuti dopo).
        connection.send_result(msg["id"], result)
        if result.get("marked_read"):
            hass.async_create_task(coordinator.async_request_refresh())
