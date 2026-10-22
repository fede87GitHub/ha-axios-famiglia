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
    AxiosStudentNotFoundError,
    AxiosStudentSwitchError,
    PortalStudent,
)
from .const import (
    CONF_COMMUNICATIONS_LIMIT,
    CONF_CUSTOMER_ID,
    CONF_PASSWORD,
    CONF_PORTAL_STUDENT,
    CONF_PORTAL_STUDENT_INDEX,
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


def _norm(value: str) -> str:
    return " ".join(str(value).split()).casefold()


class AxiosFamigliaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict = {}
        self._students: list[PortalStudent] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return AxiosFamigliaOptionsFlow()

    async def _try_login(
        self,
        data: dict,
        student_name: str | None = None,
        student_index: int | None = None,
    ) -> tuple[str | None, list[PortalStudent]]:
        """Log in to the portal (choosing the student, if given).

        Returns (error key or None, students listed by the portal).
        """
        session = ClientSession(cookie_jar=CookieJar(unsafe=True, quote_cookie=False))
        client = AxiosFamigliaClient(
            session,
            AxiosCredentials(
                customer_id=data[CONF_CUSTOMER_ID],
                username=data[CONF_USERNAME],
                password=data[CONF_PASSWORD],
            ),
            student_name=student_name,
            student_index=student_index,
        )
        try:
            await client.login()
        except AxiosAuthError:
            return "invalid_auth", []
        except AxiosRvtError:
            return "rvt_not_found", []
        except AxiosInitSequenceError:
            # Login and token extraction succeeded, but one of the
            # mandatory HeaderLoad/FooterLoad/DashboardLoad calls
            # failed. Check the HA logs for exactly which one.
            return "init_sequence_failed", []
        except AxiosStudentNotFoundError:
            return "student_not_found", []
        except AxiosStudentSwitchError:
            return "student_not_selected", []
        except AxiosApiError:
            return "cannot_connect", []
        else:
            return None, list(client.students)
        finally:
            await session.close()

    def _configured_students(self, customer_id: str, username: str) -> tuple[set[str], bool]:
        """Students already configured for this login.

        Returns (names of the entries linked to a student, whether there is an older entry that
        is not linked and therefore reads the student the portal shows after the login).
        """
        names: set[str] = set()
        has_unlinked = False
        for entry in self._async_current_entries():
            data = entry.data
            if data.get(CONF_CUSTOMER_ID) != customer_id or data.get(CONF_USERNAME) != username:
                continue
            linked = data.get(CONF_PORTAL_STUDENT)
            if linked:
                names.add(_norm(linked))
            else:
                has_unlinked = True
        return names, has_unlinked

    def _name_in_use(self, student_name: str) -> bool:
        wanted = slugify(student_name)
        return any(
            slugify(str(entry.data.get(CONF_STUDENT_NAME) or "")) == wanted
            for entry in self._async_current_entries()
        )

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input[CONF_STUDENT_NAME] = user_input[CONF_STUDENT_NAME].strip()
            student_name = user_input[CONF_STUDENT_NAME]

            if not slugify(student_name):
                errors["base"] = "invalid_name"
            elif self._name_in_use(student_name):
                errors["base"] = "name_in_use"
            else:
                error, students = await self._try_login(user_input)
                if error:
                    errors["base"] = error
                elif len(students) >= 2:
                    # Un accesso con piu' studenti: si sceglie quale mostrera' questa voce
                    self._user_input = dict(user_input)
                    self._students = students
                    return await self.async_step_student()
                else:
                    await self.async_set_unique_id(
                        f"{user_input[CONF_CUSTOMER_ID]}_{user_input[CONF_USERNAME]}"
                    )
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Axios {student_name}", data=user_input
                    )

        schema = vol.Schema({
            vol.Required(CONF_STUDENT_NAME): str,
            vol.Required(CONF_CUSTOMER_ID): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_student(self, user_input=None):
        customer_id = self._user_input[CONF_CUSTOMER_ID]
        username = self._user_input[CONF_USERNAME]
        taken, has_unlinked = self._configured_students(customer_id, username)
        # Esclusi: gli studenti gia' configurati e, se esiste una voce non legata a nessuno,
        # lo studente che quella voce sta leggendo (quello attivo dopo il login).
        available = [
            student for student in self._students
            if _norm(student.name) not in taken and not (has_unlinked and student.active)
        ]
        if not available:
            return self.async_abort(reason="all_students_configured")

        errors = {}
        if user_input is not None:
            chosen = next(
                (s for s in available if s.name == user_input[CONF_PORTAL_STUDENT]), None
            )
            if chosen is None:
                errors["base"] = "student_not_found"
            else:
                # Prova completa: login, cambio di studente e verifica che il portale lo confermi
                error, _students = await self._try_login(
                    self._user_input, chosen.name, chosen.index
                )
                if error:
                    errors["base"] = error
                else:
                    await self.async_set_unique_id(f"{customer_id}_{username}_{slugify(chosen.name)}")
                    self._abort_if_unique_id_configured()
                    data = {
                        **self._user_input,
                        CONF_PORTAL_STUDENT: chosen.name,
                        CONF_PORTAL_STUDENT_INDEX: chosen.index,
                    }
                    return self.async_create_entry(
                        title=f"Axios {self._user_input[CONF_STUDENT_NAME]}", data=data
                    )

        schema = vol.Schema({
            vol.Required(CONF_PORTAL_STUDENT, default=available[0].name): vol.In(
                [student.name for student in available]
            ),
        })
        return self.async_show_form(step_id="student", data_schema=schema, errors=errors)


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
