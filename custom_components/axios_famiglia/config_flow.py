from __future__ import annotations

import voluptuous as vol
from aiohttp import ClientSession, CookieJar

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from homeassistant.util import slugify

from .api import (
    AxiosApiError,
    AxiosAuthError,
    AxiosCredentials,
    AxiosFamigliaClient,
    AxiosInitSequenceError,
    AxiosRvtError,
)
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
    MAX_COMMUNICATIONS_LIMIT,
    MAX_REGISTER_DAYS,
    MAX_REQUEST_TIMEOUT,
    MAX_SCAN_INTERVAL,
    MIN_COMMUNICATIONS_LIMIT,
    MIN_REGISTER_DAYS,
    MIN_REQUEST_TIMEOUT,
    MIN_SCAN_INTERVAL,
)


class AxiosFamigliaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return AxiosFamigliaOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input[CONF_STUDENT_NAME] = user_input[CONF_STUDENT_NAME].strip()
            student_name = user_input[CONF_STUDENT_NAME]

            if not slugify(student_name):
                errors["base"] = "invalid_name"
            else:
                session = ClientSession(cookie_jar=CookieJar(unsafe=True, quote_cookie=False))
                client = AxiosFamigliaClient(
                    session,
                    AxiosCredentials(
                        customer_id=user_input[CONF_CUSTOMER_ID],
                        username=user_input[CONF_USERNAME],
                        password=user_input[CONF_PASSWORD],
                    ),
                )
                try:
                    await client.login()
                except AxiosAuthError:
                    errors["base"] = "invalid_auth"
                except AxiosRvtError:
                    errors["base"] = "rvt_not_found"
                except AxiosInitSequenceError:
                    # Login and token extraction succeeded, but one of the
                    # mandatory HeaderLoad/FooterLoad/DashboardLoad calls
                    # failed. Check the HA logs for exactly which one.
                    errors["base"] = "init_sequence_failed"
                except AxiosApiError:
                    errors["base"] = "cannot_connect"
                else:
                    await session.close()
                    await self.async_set_unique_id(
                        f"{user_input[CONF_CUSTOMER_ID]}_{user_input[CONF_USERNAME]}"
                    )
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Axios {student_name}", data=user_input
                    )
                await session.close()

        schema = vol.Schema({
            vol.Required(CONF_STUDENT_NAME): str,
            vol.Required(CONF_CUSTOMER_ID): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


def _number(minimum: int, maximum: int) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum, max=maximum, step=1, mode=NumberSelectorMode.BOX
        )
    )


class AxiosFamigliaOptionsFlow(config_entries.OptionsFlow):
    """Pannello delle opzioni, separato dal login e modificabile in qualsiasi momento."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # I selettori numerici restituiscono float: si salvano come interi
            return self.async_create_entry(
                title="", data={key: int(value) for key, value in user_input.items()}
            )

        options = self.config_entry.options
        schema = vol.Schema({
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): _number(MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL),
            vol.Required(
                CONF_REGISTER_DAYS,
                default=options.get(CONF_REGISTER_DAYS, DEFAULT_REGISTER_DAYS),
            ): _number(MIN_REGISTER_DAYS, MAX_REGISTER_DAYS),
            vol.Required(
                CONF_COMMUNICATIONS_LIMIT,
                default=options.get(CONF_COMMUNICATIONS_LIMIT, DEFAULT_COMMUNICATIONS_LIMIT),
            ): _number(MIN_COMMUNICATIONS_LIMIT, MAX_COMMUNICATIONS_LIMIT),
            vol.Required(
                CONF_REQUEST_TIMEOUT,
                default=options.get(CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT),
            ): _number(MIN_REQUEST_TIMEOUT, MAX_REQUEST_TIMEOUT),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
