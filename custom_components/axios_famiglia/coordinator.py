from datetime import timedelta
import logging

from aiohttp import CookieJar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AxiosApiError, AxiosCredentials, AxiosFamigliaClient
from .const import (
    CONF_CUSTOMER_ID,
    CONF_PASSWORD,
    CONF_STUDENT_NAME,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STUDENT_NAME,
    DOMAIN,
    REGISTER_DAYS,
)

_LOGGER = logging.getLogger(__name__)


class AxiosFamigliaCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.student_name: str = entry.data.get(CONF_STUDENT_NAME) or DEFAULT_STUDENT_NAME

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
            register_days=REGISTER_DAYS,
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({self.student_name})",
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        try:
            return await self.client.async_get_data()
        except AxiosApiError as err:
            raise UpdateFailed(str(err)) from err