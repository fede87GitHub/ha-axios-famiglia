from __future__ import annotations

import voluptuous as vol
from aiohttp import ClientSession, CookieJar

from homeassistant import config_entries
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
    CONF_CUSTOMER_ID,
    CONF_PASSWORD,
    CONF_STUDENT_NAME,
    CONF_USERNAME,
    DOMAIN,
)


class AxiosFamigliaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

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