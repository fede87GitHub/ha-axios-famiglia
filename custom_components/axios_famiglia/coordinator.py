from datetime import timedelta
import logging
from typing import Any

from aiohttp import CookieJar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AxiosApiError, AxiosCredentials, AxiosFamigliaClient
from .const import (
    CONF_COMMUNICATIONS_LIMIT,
    CONF_CUSTOMER_ID,
    CONF_PASSWORD,
    CONF_REGISTER_DAYS,
    CONF_REQUEST_TIMEOUT,
    CONF_SCAN_INTERVAL,
    CONF_STUDENT_NAME,
    CONF_USERNAME,
    DEFAULT_COMMUNICATIONS_LIMIT,
    DEFAULT_REGISTER_DAYS,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .items import MAX_SEEN_ITEMS, collect_items, split_new

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


class AxiosFamigliaCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.student_name: str = entry.data[CONF_STUDENT_NAME]

        # Opzioni scelte dall'utente (con i valori predefiniti se non ancora impostate)
        options = entry.options
        self.scan_interval = int(options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        self.register_days = int(options.get(CONF_REGISTER_DAYS, DEFAULT_REGISTER_DAYS))
        self.communications_limit = int(
            options.get(CONF_COMMUNICATIONS_LIMIT, DEFAULT_COMMUNICATIONS_LIMIT)
        )
        self.request_timeout = int(options.get(CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT))

        # Una sessione (e quindi un cookie jar) separata per ogni entry/studente
        self.session = async_create_clientsession(
            hass,
            cookie_jar=CookieJar(unsafe=True, quote_cookie=False),
        )
        self.client = AxiosFamigliaClient(
            self.session,
            AxiosCredentials(
                customer_id=entry.data[CONF_CUSTOMER_ID],
                username=entry.data[CONF_USERNAME],
                password=entry.data[CONF_PASSWORD],
            ),
            register_days=self.register_days,
            communications_limit=self.communications_limit,
            request_timeout=self.request_timeout,
        )

        # Rilevamento delle novità: le chiavi già viste sono salvate su disco,
        # così sopravvivono ai riavvii di Home Assistant.
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}_seen")
        self._seen: list[str] | None = None
        self._seen_loaded = False
        self.new_events: list[dict[str, Any]] = []
        self.new_events_id = 0

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({self.student_name})",
            update_interval=timedelta(minutes=self.scan_interval),
        )

    @property
    def _window(self) -> dict[str, int]:
        """Parametri che decidono QUALI voci vengono lette dal portale."""
        return {
            "register_days": self.register_days,
            "communications_limit": self.communications_limit,
        }

    async def _async_update_data(self) -> dict:
        try:
            data = await self.client.async_get_data()
        except AxiosApiError as err:
            raise UpdateFailed(str(err)) from err

        try:
            await self._async_detect_new_items(data)
        except Exception:  # noqa: BLE001
            # Un problema nel rilevamento delle novità non deve bloccare i sensori
            _LOGGER.exception("Axios: new-item detection failed")
            self.new_events = []
            self.new_events_id += 1
        return data

    async def _async_load_seen(self) -> None:
        stored = await self._store.async_load()
        seen: list[str] | None = None
        window: dict[str, Any] | None = None
        if isinstance(stored, dict):
            raw_seen = stored.get("seen")
            if isinstance(raw_seen, list):
                seen = [str(key) for key in raw_seen]
            raw_window = stored.get("window")
            if isinstance(raw_window, dict):
                window = raw_window

        if window is None:
            # File salvato da una versione precedente: usava i valori predefiniti
            window = {
                "register_days": DEFAULT_REGISTER_DAYS,
                "communications_limit": DEFAULT_COMMUNICATIONS_LIMIT,
            }

        if seen is not None and window != self._window:
            # L'utente ha cambiato quante voci vengono lette: quelle che entrano ora nella
            # finestra non sono novità, quindi si memorizzano senza notificarle.
            _LOGGER.debug(
                "Axios %s: reading window changed (%s -> %s), re-seeding without notifications",
                self.student_name, window, self._window,
            )
            seen = None

        self._seen = seen
        self._seen_loaded = True

    async def _async_detect_new_items(self, data: dict) -> None:
        if not self._seen_loaded:
            await self._async_load_seen()

        first_run = self._seen is None
        new_items, updated_seen = split_new(self._seen, collect_items(data), MAX_SEEN_ITEMS)

        if first_run or updated_seen != self._seen:
            self._seen = updated_seen
            await self._store.async_save({"seen": self._seen, "window": self._window})

        if first_run:
            _LOGGER.debug(
                "Axios %s: first run, %d items stored without notifications",
                self.student_name, len(updated_seen),
            )
        elif new_items:
            _LOGGER.debug(
                "Axios %s: %d new item(s): %s",
                self.student_name, len(new_items), [item["type"] for item in new_items],
            )

        self.new_events = new_items
        self.new_events_id += 1
