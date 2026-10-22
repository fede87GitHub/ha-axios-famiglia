from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import functools
import html as html_lib
import json
import logging
import re
import time
from typing import Any
from urllib.parse import urlsplit

from aiohttp import ClientError, ClientSession, ClientTimeout
from bs4 import BeautifulSoup
from yarl import URL

from .const import (
    AJAX_PATH,
    BASE_URL,
    DASHBOARD_INIT_ACTIONS,
    DASHBOARD_PATH_HINT,
    DEFAULT_COMMUNICATIONS_LIMIT,
    DEFAULT_FUTURE_DAYS,
    DEFAULT_REGISTER_DAYS,
    DEFAULT_REQUEST_TIMEOUT,
    LOGIN_PATH,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

_DIAG_RESPONSE_HEADERS = (
    "server", "cf-ray", "cf-cache-status", "x-powered-by",
    "x-aspnet-version", "content-length", "content-type", "date",
)

# --- Registro di classe ----------------------------------------------------
# FAMILY_REGISTRO_CLASSE mostra solo la SETTIMANA CORRENTE. Le settimane precedenti
# si leggono con FAMILY_REGISTRO_CLASSE_SETTIMANA, mandando nel corpo della richiesta
# {"fdData": "<lunedi' della settimana, gg/mm/aaaa>"}.
# Richiesta del browser (verificata con "Copy as fetch"):
#   POST .../APP_Ajax_Get.aspx?Action=FAMILY_REGISTRO_CLASSE_SETTIMANA   (senza "&_=")
#   content-type: application/x-www-form-urlencoded; charset=UTF-8
#   body: {"fdData":"19/10/2026"}
REGISTER_ACTION = "FAMILY_REGISTRO_CLASSE"
REGISTER_WEEK_ACTION = "FAMILY_REGISTRO_CLASSE_SETTIMANA"
HOMEWORK_LIST_ACTION = "FAMILY_REGISTRO_CLASSE_COMPITI_LISTA"
TOPICS_LIST_ACTION = "FAMILY_REGISTRO_CLASSE_ARGOMENTI_LISTA"
DATATABLE_PAGE_SIZE = 100
DATATABLE_MAX_RECORDS = 2000
WEEK_REQUEST_CONTENT_TYPE = "application/x-www-form-urlencoded; charset=UTF-8"
# Le settimane piu' vecchie della precedente cambiano di rado: si rileggono ogni 6 ore.
# La settimana precedente e quella corrente si leggono a ogni aggiornamento.
OLD_WEEK_CACHE_SECONDS = 6 * 60 * 60

# --- Studenti dell'accesso ---------------------------------------------------
# Un accesso al portale puo' avere piu' studenti (figli). Dalla cattura di rete di un account con
# due figlie (ottobre 2026):
#   * la risposta di DashboardLoad elenca gli studenti come link
#       <a class="change-alunno dashboard-stat [active]" data-action="FAMILY_CHANGE_ALUNNO"
#          data-others="<id dello studente>">Nome</a>
#     e quello con la classe "active" e' lo studente corrente (dopo il login, il primo).
#   * per cambiare studente il browser invia
#       POST .../APP_Ajax_Get.aspx?Action=FAMILY_CHANGE_ALUNNO     (senza "&_=")
#       content-type: application/x-www-form-urlencoded; charset=UTF-8
#       body: {"alunnoId":"<data-others del link>"}
#     e riceve {"errorcode":"0","errormsg":"...","html":"<dashboard>"} con "active" sul nuovo studente.
# NON verificato: che dopo il cambio le chiamate FAMILY_COMUNICAZIONI / FAMILY_ASSENZE /
# FAMILY_REGISTRO_CLASSE restituiscano i dati del nuovo studente (nella cattura non ci sono).
# Si presume di si', perche' quelle chiamate non portano nessun identificativo dello studente.
DASHBOARD_LOAD_ACTION = "DashboardLoad"
CHANGE_STUDENT_ACTION = "FAMILY_CHANGE_ALUNNO"

# --- Allegati delle comunicazioni -------------------------------------------
# Flusso del browser (verificato con "Copy as fetch", ottobre 2026):
#   1. POST SD/SD_Ajax_Get.aspx?Action=BACHECA_VISUALIZZA_CIRCOLARE&Others=<id>|undefined|MHx8fHw=|
#      body {}  ->  HTML della comunicazione, con un pulsante per ogni allegato (attributi data-*).
#   2. POST SD/SD_Ajax_Post.aspx?Action=SAVE_READER_POST
#      body: JSON {fiPostId, root, folder, filename, SourceFileName, fileType}
#      ->  registra la lettura: la comunicazione risulta LETTA sul portale (con data e ora) per il
#          genitore che ha fatto l'accesso. Si chiama solo quando un allegato viene davvero aperto
#          (non quando si sta solo scegliendo tra piu' allegati) e solo se MARK_AS_READ e' True.
#   3. POST COMMON/COMMON_Ajax_Get.aspx?action=DOWNLOAD_PREPARE_URL
#      body: base64 di un JSON {url, root, folder, filename, SourceFileName, fileType}
#      ->  {"errorcode":"0", "json":"<indirizzo temporaneo firmato dello storage>"}
#   Il PDF si scarica poi direttamente da quell'indirizzo (non servono cookie). L'indirizzo
#   scade dopo pochi minuti ed e' una "chiave": non va mai salvato, registrato nei log o
#   mostrato a chi non ha cliccato.
SD_AJAX_GET_PATH = "/Pages/SD/SD_Ajax_Get.aspx"
SD_AJAX_POST_PATH = "/Pages/SD/SD_Ajax_Post.aspx"
COMMON_AJAX_GET_PATH = "/Pages/COMMON/COMMON_Ajax_Get.aspx"
VIEW_CIRCULAR_ACTION = "BACHECA_VISUALIZZA_CIRCOLARE"
SAVE_READER_ACTION = "SAVE_READER_POST"
DOWNLOAD_PREPARE_ACTION = "DOWNLOAD_PREPARE_URL"
VIEW_CIRCULAR_BODY = "{}"
# Nel browser il secondo valore e' "undefined" (parametro JavaScript assente)
# e il terzo e' il base64 di "0||||"
VIEW_CIRCULAR_OTHERS_SUFFIX = "|undefined|MHx8fHw=|"
DOWNLOAD_HANDLER_URL = "../../Handlers/SD_UploadDownloadHandler.aspx"
FORM_CONTENT_TYPE = "application/x-www-form-urlencoded; charset=UTF-8"
# Interruttore GENERALE della registrazione della lettura (chiamata SAVE_READER_POST).
# True: aprendo un allegato la comunicazione puo' essere segnata come LETTA sul portale, come quando
# si clicca l'allegato nel sito. Ogni dispositivo la attiva o la spegne dalle impostazioni del
# pannello ("Segna come letta all'apertura", di base attiva).
# False: la lettura non viene MAI registrata, qualunque sia la scelta nel pannello (dove la voce
# risulta "non disponibile"). L'allegato si apre comunque.
MARK_AS_READ = True
# Il browser invia questa chiamata con l'intestazione Content-Type valorizzata letteralmente "json"
# (non e' un refuso: e' quello che si vede in "Copy as fetch"). Si replica cosi'.
SAVE_READER_CONTENT_TYPE = "json"
# Lo storage consegna il file come "scarica" (Content-Disposition: attachment). Con True si
# aggiunge "&inline" all'indirizzo, che di norma chiede di aprirlo nel visualizzatore del
# browser. Non e' stato verificato con questo storage: lasciare False se non serve.
OPEN_PDF_INLINE = False

_POST_ID_RE = re.compile(r"^[0-9]{1,15}$")
_MAX_ATTACHMENTS = 20
_MAX_URL_LENGTH = 4096
_MAX_POST_REF_LENGTH = 200
_MAX_STUDENTS = 20


def _diag_headers(headers) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() in _DIAG_RESPONSE_HEADERS}


def _today() -> date:
    return datetime.now().astimezone().date()


def mark_as_read_allowed() -> bool:
    """True when the integration allows registering the reading (MARK_AS_READ)."""
    return bool(MARK_AS_READ)


class AxiosApiError(Exception):
    """Base Axios API error."""


class AxiosAuthError(AxiosApiError):
    """Authentication failed (wrong credentials)."""


class AxiosRvtError(AxiosApiError):
    """Login succeeded but the anti-CSRF token could not be found."""


class AxiosInitSequenceError(AxiosApiError):
    """Dashboard-initialization sequence (HeaderLoad/FooterLoad/DashboardLoad) failed."""


class AxiosStudentNotFoundError(AxiosApiError):
    """The student this entry is configured for is not in the list of the account."""


class AxiosStudentSwitchError(AxiosApiError):
    """The portal did not confirm the change of student."""


def _wrap_network_errors(func):
    """Convert aiohttp/timeout errors into AxiosApiError."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (ClientError, asyncio.TimeoutError) as err:
            raise AxiosApiError(f"Network error in {func.__name__}: {err!r}") from err

    return wrapper


@dataclass
class AxiosCredentials:
    customer_id: str
    username: str
    password: str


@dataclass(frozen=True)
class PortalStudent:
    """A student of the account, as listed by the portal."""

    id: str  # value to send in FAMILY_CHANGE_ALUNNO (data-others of the link)
    name: str  # text of the link, as the portal writes it
    active: bool  # True for the student the portal is currently showing
    index: int  # position in the list


class AxiosFamigliaClient:
    """Client for the unofficial Axios Famiglia AJAX endpoints.

    Debugging history (October 2026):
      1. Cookie quoting: CookieJar(unsafe=True, quote_cookie=False).
      2. Minimal header set (no Referer, no Sec-Fetch-*, explicit User-Agent).
      3. ROOT CAUSE of the empty HTTP 400: the dashboard initialization
         sequence (HeaderLoad, FooterLoad, DashboardLoad) must be replayed
         before the first FAMILY_* call (done in `login()`).
      4. The class register page shows only the current week: previous weeks
         are read one by one with FAMILY_REGISTRO_CLASSE_SETTIMANA.
      5. An account can have several students: the one to read is chosen with
         FAMILY_CHANGE_ALUNNO right after the initialization sequence.
    """

    _USER_AGENT = USER_AGENT
    _ACCEPT_LANGUAGE = "en-US,en;q=0.9,it-IT;q=0.8,it;q=0.7"
    _AXTOKEN_PATTERNS = (
        re.compile(r"""<input[^>]*id=['"]_AXToken['"][^>]*value=['"]([^'"]+)['"]""", re.IGNORECASE),
        re.compile(r"""<input[^>]*value=['"]([^'"]+)['"][^>]*id=['"]_AXToken['"]""", re.IGNORECASE),
        re.compile(r"""<meta[^>]*name=['"]_AXToken['"][^>]*content=['"]([^'"]+)['"]""", re.IGNORECASE),
        re.compile(r"""<input[^>]*(?:name|id)=['"]rvt['"][^>]*value=['"]([^'"]+)['"]""", re.IGNORECASE),
    )

    def __init__(
        self,
        session: ClientSession,
        credentials: AxiosCredentials,
        register_days: int = DEFAULT_REGISTER_DAYS,
        future_days: int = DEFAULT_FUTURE_DAYS,
        communications_limit: int = DEFAULT_COMMUNICATIONS_LIMIT,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
        student_name: str | None = None,
        student_index: int | None = None,
    ) -> None:
        self._session = session
        self._credentials = credentials
        self._register_days = register_days
        self._future_days = future_days
        self._communications_limit = communications_limit
        self._timeout = ClientTimeout(total=request_timeout)
        self._logged_in = False
        self._dashboard_url: str | None = None
        self._rvt: str | None = None
        # monday of the week -> (time of the reading, rows)
        self._week_cache: dict[date, tuple[float, list[dict[str, Any]]]] = {}
        self._weeks_warned = False
        # Studente da leggere: None = quello che il portale mostra dopo il login (comportamento
        # delle voci create prima del supporto a piu' studenti).
        self._student_name = (student_name or "").strip() or None
        self._student_index = student_index
        self._students_warned = False
        self.students: list[PortalStudent] = []
        self.selected_student: PortalStudent | None = None
        # Un solo discorso alla volta con il portale: l'aggiornamento periodico e l'apertura
        # di un allegato usano la stessa sessione e, se scade, lo stesso login.
        self._lock = asyncio.Lock()

    def _ajax_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": self._ACCEPT_LANGUAGE,
            "Content-Type": "application/json; charset=utf-8",
            "Priority": "u=1, i",
            "User-Agent": self._USER_AGENT,
            "X-Requested-With": "XMLHttpRequest",
        }
        if self._rvt:
            headers["rvt"] = self._rvt
        return headers

    @_wrap_network_errors
    async def login(self) -> None:
        _LOGGER.debug(
            "Axios login: starting fresh login as %s / customer %s",
            self._credentials.username, self._credentials.customer_id,
        )
        self._logged_in = False
        login_page_url = f"{BASE_URL}{LOGIN_PATH}"

        async with self._session.get(
            login_page_url,
            headers={"User-Agent": self._USER_AGENT},
            timeout=self._timeout,
        ) as response:
            if response.status >= 400:
                raise AxiosApiError(f"Login page returned HTTP {response.status}")
            await response.read()

        payload = {
            "customerid": self._credentials.customer_id,
            "username": self._credentials.username,
            "password": self._credentials.password,
            "customeridSpid": "",
        }
        async with self._session.post(
            login_page_url,
            data=payload,
            headers={
                "User-Agent": self._USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            allow_redirects=False,
            timeout=self._timeout,
        ) as response:
            location = response.headers.get("Location", "")
            if response.status not in (301, 302, 303) or DASHBOARD_PATH_HINT not in location:
                snippet = (await response.text())[:500]
                raise AxiosAuthError(
                    f"Login rejected (HTTP {response.status}); body={snippet!r}"
                )
            self._dashboard_url = (
                location if location.startswith("http") else f"{BASE_URL}{location}"
            )

        async with self._session.get(
            self._dashboard_url,
            headers={"User-Agent": self._USER_AGENT},
            timeout=self._timeout,
        ) as response:
            if response.status >= 400:
                raise AxiosAuthError(f"Dashboard returned HTTP {response.status}")
            dashboard_html = await response.text()

        self._rvt = self._extract_axtoken(dashboard_html)
        if not self._rvt:
            raise AxiosRvtError(
                "Login succeeded (credentials are correct) but the '_AXToken' "
                "anti-CSRF value was not found in the dashboard page. "
                f"Dashboard length: {len(dashboard_html)} chars."
            )
        _LOGGER.debug("Axios login: _AXToken found (len=%d)", len(self._rvt))

        dashboard_load_html = ""
        for init_action in DASHBOARD_INIT_ACTIONS:
            try:
                result = await self._raw_action(init_action, require_json=False)
            except AxiosApiError as err:
                _LOGGER.error(
                    "Axios login: dashboard init call '%s' FAILED: %s", init_action, err,
                )
                raise AxiosInitSequenceError(
                    f"Dashboard initialization call '{init_action}' failed: {err}"
                ) from err
            if init_action == DASHBOARD_LOAD_ACTION:
                dashboard_load_html = result
            _LOGGER.debug("Axios login: dashboard init call '%s' completed", init_action)

        # La risposta di DashboardLoad elenca gli studenti dell'accesso: si legge qui, senza
        # richieste in piu', e se serve si passa allo studente scelto.
        self.students = parse_students(dashboard_load_html)
        await self._ensure_student()
        self._logged_in = True

    async def _ensure_student(self) -> None:
        """Make sure the portal is showing the student this client is configured for."""
        active = next((s for s in self.students if s.active), None)
        self.selected_student = active
        if not self._student_name:
            return  # comportamento di sempre: si legge lo studente che il portale mostra
        if not self.students:
            if not self._students_warned:
                self._students_warned = True
                _LOGGER.warning(
                    "Axios: the portal did not list the students of the account, so the student "
                    "cannot be chosen. The data of the student shown by the portal is used."
                )
            return

        target = resolve_student(self.students, self._student_name, self._student_index)
        self.selected_student = target
        if target.active:
            _LOGGER.debug(
                "Axios login: the wanted student (position %d of %d) is already the active one",
                target.index + 1, len(self.students),
            )
            return

        _LOGGER.debug(
            "Axios login: switching to the student in position %d of %d",
            target.index + 1, len(self.students),
        )
        body = json.dumps({"alunnoId": target.id}, separators=(",", ":"))
        raw_html = await self._raw_action(CHANGE_STUDENT_ACTION, require_json=False, body=body)
        after = parse_students(raw_html)
        if not after:
            # La risposta non permette di verificare: non e' un errore sicuro, ma va segnalato.
            _LOGGER.warning(
                "Axios: the portal answered the change of student but the answer does not allow "
                "to confirm it (response starts with %r)",
                raw_html[:120],
            )
            return
        now_active = next((s for s in after if s.active), None)
        if now_active is None or now_active.id != target.id:
            raise AxiosStudentSwitchError(
                "The portal did not confirm the change of student "
                f"(wanted position {target.index + 1} of {len(after)})"
            )
        self.students = after
        self.selected_student = now_active

    @classmethod
    def _extract_axtoken(cls, html_text: str) -> str | None:
        for pattern in cls._AXTOKEN_PATTERNS:
            match = pattern.search(html_text)
            if match:
                return match.group(1)
        return None

    @_wrap_network_errors
    async def _raw_action(
        self, action: str, require_json: bool = True, body: str | None = None
    ) -> str:
        """One APP_Ajax_Get.aspx call, without the logged_in/retry logic.

        GET by default (with the "_" cache-buster the browser adds); POST when `body` is
        given (used to read a past register week and to change student). The browser's POST
        has NO "_" parameter.
        """
        headers = self._ajax_headers()
        url = f"{BASE_URL}{AJAX_PATH}"
        if body is None:
            request = self._session.get(
                url,
                params={"Action": action, "_": str(int(time.time() * 1000))},
                headers=headers,
                timeout=self._timeout,
            )
        else:
            headers["Content-Type"] = WEEK_REQUEST_CONTENT_TYPE
            request = self._session.post(
                url,
                params={"Action": action},
                data=body.encode("utf-8"),
                headers=headers,
                timeout=self._timeout,
            )
        async with request as response:
            if response.status >= 400:
                snippet = (await response.text())[:500]
                raise AxiosApiError(
                    f"{action} returned HTTP {response.status}: body={snippet!r}; "
                    f"response_headers={_diag_headers(response.headers)}"
                )
            raw_body = await response.text()
            try:
                payload: Any = json.loads(raw_body)
            except Exception as err:  # noqa: BLE001
                # Il contenuto NON va nel log: le risposte HTML (per esempio DashboardLoad)
                # contengono i nomi degli studenti, e chi segnala un problema incolla i log.
                _LOGGER.debug(
                    "Axios action %s: response was not JSON (content-type=%s, %d chars)",
                    action, response.headers.get("Content-Type"), len(raw_body),
                )
                if require_json:
                    raise AxiosApiError(
                        f"Invalid (non-JSON) response for {action}: {raw_body[:300]!r}"
                    ) from err
                return raw_body

        if not isinstance(payload, dict):
            raise AxiosApiError(f"Unexpected JSON response for {action}: {raw_body[:300]!r}")
        if str(payload.get("errorcode", "0")) != "0":
            raise AxiosApiError(str(payload.get("errormsg", "Unknown Axios error")))
        return html_lib.unescape(str(payload.get("html", "")))

    async def _action(self, action: str) -> str:
        if not self._logged_in:
            await self.login()
        try:
            return await self._raw_action(action)
        except AxiosApiError:
            # Session may have expired: retry once after a fresh login
            # (which also chooses the student again).
            self._logged_in = False
            await self.login()
            return await self._raw_action(action)

    async def _raw_datatable_page(self, action: str, start: int) -> dict[str, Any]:
        """Read one structured DataTables page from Axios."""
        headers = self._ajax_headers()
        headers["Content-Type"] = WEEK_REQUEST_CONTENT_TYPE
        body = json.dumps(
            {
                "draw": start // DATATABLE_PAGE_SIZE + 1,
                "columns": {},
                "order": [],
                "start": start,
                "length": DATATABLE_PAGE_SIZE,
                "search": {"value": "", "regex": False},
                "iMatId": "",
            },
            separators=(",", ":"),
        )
        url = f"{BASE_URL}{AJAX_PATH}"
        async with self._session.post(
            url,
            params={"Action": action},
            data=body.encode("utf-8"),
            headers=headers,
            timeout=self._timeout,
        ) as response:
            if response.status >= 400:
                snippet = (await response.text())[:300]
                raise AxiosApiError(f"{action} returned HTTP {response.status}: {snippet!r}")
            raw = await response.text()
        try:
            payload = json.loads(raw)
        except ValueError as err:
            raise AxiosApiError(f"Invalid JSON response for {action}") from err
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise AxiosApiError(f"Unexpected DataTables response for {action}")
        return payload

    async def _datatable_action(self, action: str) -> list[dict[str, Any]]:
        """Read every page of a structured Axios DataTables endpoint."""
        if not self._logged_in:
            await self.login()
        try:
            return await self._read_datatable_pages(action)
        except AxiosApiError:
            self._logged_in = False
            await self.login()
            return await self._read_datatable_pages(action)

    async def _read_datatable_pages(self, action: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        start = 0
        while start < DATATABLE_MAX_RECORDS:
            page = await self._raw_datatable_page(action, start)
            rows = [row for row in page["data"] if isinstance(row, dict)]
            records.extend(rows)
            try:
                total = int(page.get("recordsFiltered", page.get("recordsTotal", len(records))))
            except (TypeError, ValueError):
                total = len(records)
            if not rows or len(records) >= total:
                break
            start += len(rows)
        if start >= DATATABLE_MAX_RECORDS:
            _LOGGER.warning("Axios %s: stopped after %d records", action, len(records))
        return records[:DATATABLE_MAX_RECORDS]

    async def _fetch_week(self, monday: date) -> list[dict[str, Any]]:
        """Register rows of the week starting on `monday`."""
        fd_data = monday.strftime("%d/%m/%Y")
        body = json.dumps({"fdData": fd_data}, separators=(",", ":"))
        raw_html = await self._raw_action(REGISTER_WEEK_ACTION, require_json=False, body=body)
        rows = parse_register_rows(raw_html)
        _LOGGER.debug("Axios register week %s: %d rows", fd_data, len(rows))
        if not rows:
            _LOGGER.debug(
                "Axios register week %s: no rows found; response starts with %r",
                fd_data, raw_html[:300],
            )
        return rows

    async def _read_extra_weeks(self) -> tuple[list[dict[str, Any]], bool]:
        """Rows outside the current week that fall in the past/future windows.

        Returns (rows, complete). A week that cannot be read never breaks the update:
        its last known rows are used if there are any, otherwise it is skipped.
        Past weeks older than the immediately previous one are cached for six hours;
        the previous and future weeks are refreshed at every coordinator update.
        """
        today = _today()
        this_monday = today - timedelta(days=today.weekday())
        mondays = extra_week_mondays(today, self._register_days, self._future_days)
        for stale in [m for m in self._week_cache if m not in mondays]:
            del self._week_cache[stale]

        rows: list[dict[str, Any]] = []
        first_error: AxiosApiError | None = None
        for monday in reversed(mondays):  # previous week first
            cached = self._week_cache.get(monday)
            is_old = monday < this_monday - timedelta(days=7)
            if (
                cached is not None
                and is_old
                and time.monotonic() - cached[0] < OLD_WEEK_CACHE_SECONDS
            ):
                rows.extend(cached[1])
                continue
            try:
                week_rows = await self._fetch_week(monday)
            except AxiosApiError as err:
                first_error = first_error or err
                if cached is not None:
                    rows.extend(cached[1])
                continue
            self._week_cache[monday] = (time.monotonic(), week_rows)
            rows.extend(week_rows)

        complete = first_error is None
        if complete:
            self._weeks_warned = False
        elif not self._weeks_warned:
            self._weeks_warned = True
            _LOGGER.warning(
                "Axios register: could not read the previous weeks (%s). "
                "Only the weeks already read are shown. Enable debug logs for details.",
                first_error,
            )
        else:
            _LOGGER.debug("Axios register: previous weeks still unavailable (%s)", first_error)
        return rows, complete

    async def async_get_data(self) -> dict[str, Any]:
        async with self._lock:
            communications_html = await self._action("FAMILY_COMUNICAZIONI")
            absences_html = await self._action("FAMILY_ASSENZE")
            # The current week comes from the call that is known to work; the previous
            # weeks (if any are needed) are added after it.
            register_html = await self._action(REGISTER_ACTION)
            current_rows = parse_register_rows(register_html)
            extra_rows, complete = await self._read_extra_weeks()
            homework_raw = await self._datatable_action(HOMEWORK_LIST_ACTION)
            topics_raw = await self._datatable_action(TOPICS_LIST_ACTION)
        rows = merge_register_rows(current_rows, extra_rows)
        schoolwork = build_structured_schoolwork(
            homework_raw, self._register_days, self._future_days
        )
        topics = build_structured_topics(
            topics_raw, self._register_days, self._future_days
        )
        return {
            "communications": parse_communications(
                communications_html, self._communications_limit
            ),
            "absences": parse_absences(absences_html),
            "register": build_register(
                rows, self._register_days, self._future_days, partial=not complete
            ),
            "schoolwork": schoolwork,
            "topics": topics,
            "updated_at": datetime.now().astimezone().isoformat(),
        }

    # ------------------------------------------------------------------ allegati
    @_wrap_network_errors
    async def _post_text(
        self,
        url: URL | str,
        *,
        accept: str,
        body: str,
        what: str,
        content_type: str = FORM_CONTENT_TYPE,
    ) -> str:
        """POST like the browser does for the SD_* / COMMON_* endpoints; returns the body text."""
        headers = {
            "Accept": accept,
            "Accept-Language": self._ACCEPT_LANGUAGE,
            "Content-Type": content_type,
            "Priority": "u=1, i",
            "User-Agent": self._USER_AGENT,
            "X-Requested-With": "XMLHttpRequest",
        }
        if self._rvt:
            headers["rvt"] = self._rvt
        async with self._session.post(
            url, data=body.encode("utf-8"), headers=headers, timeout=self._timeout
        ) as response:
            if response.status >= 400:
                snippet = (await response.text())[:300]
                raise AxiosApiError(
                    f"{what} returned HTTP {response.status}: body={snippet!r}; "
                    f"response_headers={_diag_headers(response.headers)}"
                )
            return await response.text()

    async def _fetch_attachments(self, post_id: str) -> list[dict[str, str]]:
        # L'indirizzo e' scritto a mano e passato "gia' codificato": e' identico a quello del
        # browser (con le barre verticali e il "=" finale del base64 non convertiti).
        url = URL(
            f"{BASE_URL}{SD_AJAX_GET_PATH}?Action={VIEW_CIRCULAR_ACTION}"
            f"&Others={post_id}{VIEW_CIRCULAR_OTHERS_SUFFIX}",
            encoded=True,
        )
        raw = await self._post_text(
            url, accept="text/html, */*; q=0.01", body=VIEW_CIRCULAR_BODY, what=VIEW_CIRCULAR_ACTION
        )
        if raw.lstrip().startswith("{"):
            # Nel caso il portale avvolga l'HTML in una busta JSON come le altre chiamate
            try:
                envelope = json.loads(raw)
            except ValueError:
                envelope = None
            if isinstance(envelope, dict):
                raw = html_lib.unescape(str(envelope.get("html", "")))
        if "modal-title" not in raw and "modal-body" not in raw:
            # Non e' la pagina di una comunicazione: tipicamente la sessione e' scaduta
            raise AxiosApiError(
                f"Unexpected response for {VIEW_CIRCULAR_ACTION} (response starts with {raw[:200]!r})"
            )
        attachments = parse_attachments(raw)
        if not attachments:
            _LOGGER.debug(
                "Axios communication %s: no attachments found in the page (%d chars)",
                post_id, len(raw),
            )
        return attachments

    async def _read_attachments(self, post_id: str) -> list[dict[str, str]]:
        if not self._logged_in:
            await self.login()
        try:
            return await self._fetch_attachments(post_id)
        except AxiosApiError:
            # Session may have expired: retry once after a fresh login.
            self._logged_in = False
            await self.login()
            return await self._fetch_attachments(post_id)

    async def _mark_as_read(self, attachment: dict[str, str]) -> bool:
        """Register the reading on the portal (SAVE_READER_POST), like the browser does.

        Never raises: if it fails the attachment is opened anyway. Returns True when the
        portal confirmed the reading.
        """
        if not MARK_AS_READ:
            return False
        body = build_save_reader_body(attachment)
        if body is None:
            _LOGGER.debug(
                "Axios attachment: the page has no post reference, the communication is not marked as read"
            )
            return False
        try:
            raw = await self._post_text(
                f"{BASE_URL}{SD_AJAX_POST_PATH}?Action={SAVE_READER_ACTION}",
                accept="application/json, text/javascript, */*; q=0.01",
                body=body,
                what=SAVE_READER_ACTION,
                content_type=SAVE_READER_CONTENT_TYPE,
            )
            check_save_reader_response(raw)
        except AxiosApiError as err:
            _LOGGER.warning(
                "Axios: the communication could not be marked as read (%s). "
                "The attachment is opened anyway.",
                err,
            )
            return False
        _LOGGER.debug("Axios attachment: the communication was marked as read")
        return True

    async def _prepare_download(self, attachment: dict[str, str]) -> str:
        raw = await self._post_text(
            f"{BASE_URL}{COMMON_AJAX_GET_PATH}?action={DOWNLOAD_PREPARE_ACTION}",
            accept="application/json, text/javascript, */*; q=0.01",
            body=build_download_body(attachment),
            what=DOWNLOAD_PREPARE_ACTION,
        )
        url = parse_download_url(raw)
        _LOGGER.debug("Axios attachment: temporary link obtained (host %s)", urlsplit(url).hostname)
        return url

    async def async_open_attachment(
        self,
        post_id: str,
        attachment_id: str | None = None,
        mark_read: bool | None = None,
    ) -> dict[str, Any]:
        """Prepare the opening of the attachment of a communication.

        `mark_read` is the choice made in the settings of the panel on that device:
        False -> the reading is not registered; True or None -> it is registered, unless
        the general switch MARK_AS_READ is off.

        Returns one of:
          {"status": "none"}                                  no attachment
          {"status": "choose", "attachments": [{id, name}]}   several attachments: choose one
          {"status": "ok", "url": ..., "name": ..., "marked_read": bool}
                                                              temporary link, valid a few minutes

        Raises ValueError for an invalid id and AxiosApiError when the portal fails.
        """
        post_id = validate_post_id(post_id)
        async with self._lock:
            attachments = await self._read_attachments(post_id)
            if not attachments:
                return {"status": "none"}
            if attachment_id is None:
                if len(attachments) > 1:
                    return {
                        "status": "choose",
                        "attachments": [
                            {"id": item["filename"], "name": item["name"]} for item in attachments
                        ],
                    }
                chosen = attachments[0]
            else:
                chosen = next(
                    (item for item in attachments if item["filename"] == attachment_id), None
                )
                if chosen is None:
                    raise AxiosApiError("Attachment not found in the communication")
            marked_read = False if mark_read is False else await self._mark_as_read(chosen)
            url = await self._prepare_download(chosen)
        return {
            "status": "ok",
            "url": apply_inline(url),
            "name": chosen["name"],
            "marked_read": marked_read,
        }


def _text(node: Any) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def _norm_name(value: str) -> str:
    return " ".join(str(value).split()).casefold()


def parse_students(raw_html: str) -> list[PortalStudent]:
    """Students listed by the portal: links a.change-alunno with data-action FAMILY_CHANGE_ALUNNO.

    The link with the class "active" is the student the portal is showing. An account with a
    single student may not list any link at all: the result is then an empty list.
    """
    soup = BeautifulSoup(raw_html or "", "html.parser")
    students: list[PortalStudent] = []
    seen: set[str] = set()
    for node in soup.select("a.change-alunno"):
        if str(node.get("data-action", "")).strip().upper() != CHANGE_STUDENT_ACTION:
            continue
        student_id = str(node.get("data-others", "")).strip()
        name = _text(node)
        if not student_id or not name or student_id in seen:
            continue
        seen.add(student_id)
        classes = node.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        students.append(
            PortalStudent(id=student_id, name=name, active="active" in classes, index=len(students))
        )
        if len(students) >= _MAX_STUDENTS:
            break
    return students


def resolve_student(
    students: list[PortalStudent], name: str, index: int | None = None
) -> PortalStudent:
    """The student with the given name. With homonyms, the stored position decides.

    Raises AxiosStudentNotFoundError (without writing any name in the message).
    """
    wanted = _norm_name(name)
    matches = [student for student in students if _norm_name(student.name) == wanted]
    if not matches:
        raise AxiosStudentNotFoundError(
            f"The student of this entry is not among the {len(students)} students of the account"
        )
    if len(matches) > 1 and index is not None:
        for student in matches:
            if student.index == index:
                return student
    return matches[0]


def parse_communications(
    raw_html: str, limit: int = DEFAULT_COMMUNICATIONS_LIMIT
) -> dict[str, Any]:
    soup = BeautifulSoup(raw_html, "html.parser")
    items: list[dict[str, Any]] = []
    for row in soup.select("li[data-post-id]"):
        post_id = row.get("data-post-id", "")
        title_node = row.select_one(".col-md-6 b")
        author_node = row.select_one(".col-md-6 small")
        status_node = row.select_one(".label-lettura")
        date_parts = [
            _text(node) for node in row.select(".col-md-2 .text-center > div")[:3]
        ]
        item_type = _text(row.select_one(".col-md-2 .text-center .label"))
        if not title_node:
            continue
        items.append({
            "id": post_id,
            "title": _text(title_node),
            "author": _text(author_node).removeprefix("Pubblicata da:").strip(),
            "status": _text(status_node),
            "unread": _text(status_node).lower() == "non letta",
            "date": " ".join(part for part in date_parts if part),
            "type": item_type,
        })
    return {
        # Totale e non lette contano tutte le comunicazioni del portale;
        # solo l'elenco e' limitato.
        "total": len(items),
        "unread": sum(1 for item in items if item["unread"]),
        "latest": items[0] if items else None,
        "items": items[:limit],
    }


def validate_post_id(post_id: Any) -> str:
    """The id of a communication goes into the URL of the portal: digits only."""
    value = str(post_id).strip() if post_id is not None else ""
    if not _POST_ID_RE.match(value):
        raise ValueError("Invalid communication id")
    return value


def _b64decode_text(value: str) -> str:
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), validate=False)
        return raw.decode("utf-8").strip()
    except (ValueError, UnicodeDecodeError):
        return ""


def parse_attachments(raw_html: str) -> list[dict[str, str]]:
    """Attachments of a communication page: one download button each (attributes data-*).

    Values are stripped: the portal writes them as data-root=' 123 ' with spaces inside the quotes.
    The attribute postId (lowercased by the parser) is the reference needed by SAVE_READER_POST.
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    found: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def attr(node: Any, name: str) -> str:
        value = node.get(name)
        if isinstance(value, list):
            value = " ".join(value)
        return str(value or "").strip()

    for node in soup.find_all(attrs={"data-storage-filename": True}):
        filename = attr(node, "data-storage-filename") or attr(node, "data-filename")
        root = attr(node, "data-root")
        folder = attr(node, "data-folder")
        if not (filename and root and folder):
            continue
        key = (folder, filename)
        if key in seen:
            continue
        seen.add(key)
        source = attr(node, "data-source-filename")
        name = _b64decode_text(source) if source else ""
        name = name or attr(node, "title") or filename
        if not source:
            source = base64.b64encode(name.encode("utf-8")).decode("ascii")
        post_ref = attr(node, "postid") or attr(node, "data-postid")
        found.append({
            "root": root,
            "folder": folder,
            "filename": filename,
            "source": source,
            "file_type": attr(node, "data-filetype") or "0",
            "post_ref": post_ref[:_MAX_POST_REF_LENGTH],
            "name": name[:200],
        })
        if len(found) >= _MAX_ATTACHMENTS:
            break
    return found


def build_download_body(attachment: dict[str, str]) -> str:
    """Body of DOWNLOAD_PREPARE_URL: base64 of a compact JSON, keys in the browser's order."""
    payload = {
        "url": DOWNLOAD_HANDLER_URL,
        "root": attachment["root"],
        "folder": attachment["folder"],
        "filename": attachment["filename"],
        "SourceFileName": attachment["source"],
        "fileType": attachment["file_type"],
    }
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def build_save_reader_body(attachment: dict[str, str]) -> str | None:
    """Body of SAVE_READER_POST: a compact JSON, keys in the browser's order.

    None when the page did not carry the post reference (fiPostId): without it the call
    cannot be made.
    """
    post_ref = attachment.get("post_ref", "")
    if not post_ref:
        return None
    payload = {
        "fiPostId": post_ref,
        "root": attachment["root"],
        "folder": attachment["folder"],
        "filename": attachment["filename"],
        "SourceFileName": attachment["source"],
        "fileType": attachment["file_type"],
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def check_save_reader_response(raw: str) -> None:
    """The response of SAVE_READER_POST is {"errorcode":"0", "errormsg":"Errore [{0}] - {1}", "json":""}.

    The errormsg is a placeholder template and is present even on success: only errorcode counts.
    """
    try:
        payload = json.loads(raw)
    except ValueError as err:
        raise AxiosApiError("Invalid (non-JSON) response for SAVE_READER_POST") from err
    if not isinstance(payload, dict):
        raise AxiosApiError("Unexpected JSON response for SAVE_READER_POST")
    if str(payload.get("errorcode", "0")) != "0":
        raise AxiosApiError(str(payload.get("errormsg", "Unknown Axios error")))


def parse_download_url(raw: str) -> str:
    """The temporary link from the DOWNLOAD_PREPARE_URL response.

    Error messages never contain the link: it works as a key until it expires.
    """
    try:
        payload = json.loads(raw)
    except ValueError as err:
        raise AxiosApiError("Invalid (non-JSON) response for DOWNLOAD_PREPARE_URL") from err
    if not isinstance(payload, dict):
        raise AxiosApiError("Unexpected JSON response for DOWNLOAD_PREPARE_URL")
    if str(payload.get("errorcode", "0")) != "0":
        raise AxiosApiError(str(payload.get("errormsg", "Unknown Axios error")))
    url = payload.get("json")
    if not isinstance(url, str) or not url.strip():
        raise AxiosApiError("DOWNLOAD_PREPARE_URL did not return a link")
    url = url.strip()
    try:
        parts = urlsplit(url)
        host = parts.hostname
        has_credentials = bool(parts.username or parts.password)
    except ValueError as err:
        raise AxiosApiError("DOWNLOAD_PREPARE_URL returned an invalid link") from err
    if (
        parts.scheme != "https"
        or not host
        or has_credentials
        or len(url) > _MAX_URL_LENGTH
        or any(char in url for char in " \t\r\n\"'<>\\")
    ):
        raise AxiosApiError("DOWNLOAD_PREPARE_URL returned a link that was not accepted")
    return url


def apply_inline(url: str) -> str:
    """Optionally ask the storage to show the file in the browser instead of downloading it."""
    if not OPEN_PDF_INLINE or "inline" in urlsplit(url).query.split("&"):
        return url
    return f"{url}{'&' if '?' in url else '?'}inline"


def parse_absences(raw_html: str) -> dict[str, Any]:
    soup = BeautifulSoup(raw_html, "html.parser")
    summary: dict[str, Any] = {
        "absences": 0, "late_entries": 0, "early_exits": 0,
        "percentage": 0.0, "events": [],
    }
    labels = {
        "assenze totali": "absences",
        "ritardi totali": "late_entries",
        "uscite anticipate totali": "early_exits",
        "percentuale assenze": "percentage",
    }
    for box in soup.select(".summary-box"):
        label = _text(box.select_one(".summary-label")).lower()
        value = _text(box.select_one(".summary-value"))
        key = next((mapped for text, mapped in labels.items() if text in label), None)
        if not key:
            continue
        if key == "percentage":
            summary[key] = float(value.replace("%", "").replace(",", ".") or 0)
        else:
            summary[key] = int(re.sub(r"\D", "", value) or 0)
    for row in soup.select(".absence-dashboard table tbody tr"):
        cells = row.find_all("td")
        if len(cells) >= 3:
            summary["events"].append({
                "date": _text(cells[0]),
                "description": _text(cells[1]),
                "counts": _text(cells[2]).upper() == "SI",
            })
    summary["latest"] = summary["events"][0] if summary["events"] else None
    return summary


_ISO_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_IT_DATE_RE = re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})")


def _parse_date(text: str) -> date | None:
    """Extract a date from '09/10/2026', '9-10-26' or '2026-10-09'."""
    try:
        match = _ISO_DATE_RE.search(text)
        if match:
            year, month, day = (int(g) for g in match.groups())
            return date(year, month, day)
        match = _IT_DATE_RE.search(text)
        if match:
            day, month, year = (int(g) for g in match.groups())
            if year < 100:
                year += 2000
            return date(year, month, day)
    except ValueError:
        return None
    return None


def _limit_register_days(
    days: list[dict[str, Any]], past_days: int, future_days: int
) -> list[dict[str, Any]]:
    """Keep rows inside the rolling past/future window (newest first).

    If a date cannot be parsed, fall back to the first `past_days + future_days` rows.
    """
    if not days:
        return days
    parsed = [(_parse_date(day["date"]), day) for day in days]
    if all(day_date is not None for day_date, _ in parsed):
        today = _today()
        first_day = today - timedelta(days=max(0, past_days))
        last_day = today + timedelta(days=max(0, future_days))
        selected = [(d, row) for d, row in parsed if first_day <= d <= last_day]
        selected.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in selected]
    _LOGGER.warning(
        "Axios register: could not parse all dates (example: %r); "
        "falling back to the first %d rows",
        days[0]["date"], past_days + future_days,
    )
    return days[: past_days + future_days]


def past_week_mondays(today: date, limit_days: int) -> list[date]:
    """Mondays (oldest first) of the weeks BEFORE the current one that overlap
    the last `limit_days` days. The current week is read by the main call."""
    if limit_days <= 0:
        return []
    this_monday = today - timedelta(days=today.weekday())
    first = today - timedelta(days=limit_days)
    monday = first - timedelta(days=first.weekday())
    mondays: list[date] = []
    while monday < this_monday:
        mondays.append(monday)
        monday += timedelta(days=7)
    return mondays


def future_week_mondays(today: date, future_days: int) -> list[date]:
    """Mondays of future weeks overlapping the next `future_days` days.

    The current week is deliberately excluded because FAMILY_REGISTRO_CLASSE already
    returns it. For example, on Friday with future_days=7, the next Monday is included.
    """
    if future_days <= 0:
        return []
    this_monday = today - timedelta(days=today.weekday())
    last_day = today + timedelta(days=future_days)
    monday = this_monday + timedelta(days=7)
    mondays: list[date] = []
    while monday <= last_day:
        mondays.append(monday)
        monday += timedelta(days=7)
    return mondays


def extra_week_mondays(today: date, past_days: int, future_days: int) -> list[date]:
    """All non-current weeks required by the configured past/future windows."""
    return past_week_mondays(today, past_days) + future_week_mondays(today, future_days)


def parse_register_rows(raw_html: str) -> list[dict[str, Any]]:
    """The rows (one per school day) of a register page or of a single week."""
    soup = BeautifulSoup(raw_html, "html.parser")
    table = soup.select_one("#table-rcla")
    rows = table.select("tbody tr") if table else []
    only_dated = False
    if not rows:
        # The weekly response may not wrap the rows in the same table:
        # accept any row with 7 cells whose first cell is a date.
        rows = soup.select("tr")
        only_dated = True
    days: list[dict[str, Any]] = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 7:
            continue
        date_text = _text(cells[0])
        if only_dated and _parse_date(date_text) is None:
            continue
        days.append({
            "date": date_text,
            "topics": _text(cells[1]),
            "homework": _text(cells[2]),
            "tests": _text(cells[3]),
            "absences": _text(cells[4]),
            "annotations": _text(cells[5]),
            "disciplinary_notes": _text(cells[6]),
        })
    return days


def merge_register_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Join the rows of several pages, keeping the first row seen for each day."""
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for row in group:
            parsed = _parse_date(row["date"])
            key = parsed.isoformat() if parsed else row["date"]
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
    return merged


def build_register(
    rows: list[dict[str, Any]],
    limit_days: int = DEFAULT_REGISTER_DAYS,
    future_days: int = 0,
    partial: bool = False,
) -> dict[str, Any]:
    total_rows = len(rows)
    days = _limit_register_days(rows, limit_days, future_days)
    _LOGGER.debug(
        "Axios register: kept %d of %d rows (past %d days, future %d days)",
        len(days), total_rows, limit_days, future_days,
    )

    homework = [d for d in days if d["homework"] or d["tests"]]
    annotations = [d for d in days if d["annotations"]]
    notes = [d for d in days if d["disciplinary_notes"]]
    return {
        "window_days": limit_days,
        "future_days": future_days,
        "partial": partial,
        "days": days,
        "homework_count": len(homework),
        "annotation_count": len(annotations),
        "disciplinary_note_count": len(notes),
        "homework": homework,
        "annotations": annotations,
        "disciplinary_notes": notes,
    }


def _clean_portal_text(value: Any) -> str:
    """Decode Axios HTML entities and normalize whitespace without losing wording."""
    return " ".join(html_lib.unescape(str(value or "")).split())


def _inside_window(raw_date: str, past_days: int, future_days: int) -> bool:
    parsed = _parse_date(raw_date)
    if parsed is None:
        return False
    today = _today()
    return today - timedelta(days=max(0, past_days)) <= parsed <= today + timedelta(days=max(0, future_days))


def build_structured_schoolwork(
    records: list[dict[str, Any]], past_days: int, future_days: int
) -> dict[str, Any]:
    """Normalize the structured homework/test endpoint, one item per subject and type."""
    items: list[dict[str, str]] = []
    for row in records:
        raw_date = _clean_portal_text(row.get("giorno"))
        if not _inside_window(raw_date, past_days, future_days):
            continue
        subject = _clean_portal_text(row.get("materia"))
        author = _clean_portal_text(row.get("inserito"))
        homework = _clean_portal_text(row.get("testo"))
        test = _clean_portal_text(row.get("verifica"))
        if homework:
            items.append({"date": raw_date, "subject": subject, "text": homework, "author": author, "type": "homework"})
        if test:
            items.append({"date": raw_date, "subject": subject, "text": test, "author": author, "type": "test"})
    items.sort(key=lambda x: _parse_date(x["date"]) or date.min, reverse=True)
    return {
        "window_days": past_days,
        "future_days": future_days,
        "items": items,
        "homework_count": sum(item["type"] == "homework" for item in items),
        "test_count": sum(item["type"] == "test" for item in items),
    }


def build_structured_topics(
    records: list[dict[str, Any]], past_days: int, future_days: int
) -> dict[str, Any]:
    """Normalize the structured lesson-topics endpoint, one item per subject."""
    items: list[dict[str, str]] = []
    for row in records:
        raw_date = _clean_portal_text(row.get("giorno"))
        text = _clean_portal_text(row.get("testo"))
        if not text or not _inside_window(raw_date, past_days, future_days):
            continue
        items.append({
            "date": raw_date,
            "subject": _clean_portal_text(row.get("materia")),
            "text": text,
            "author": _clean_portal_text(row.get("inserito")),
        })
    items.sort(key=lambda x: _parse_date(x["date"]) or date.min, reverse=True)
    return {"window_days": past_days, "future_days": future_days, "items": items}


def parse_register(
    raw_html: str,
    limit_days: int = DEFAULT_REGISTER_DAYS,
    future_days: int = 0,
) -> dict[str, Any]:
    """Single page (the current week): kept for compatibility."""
    return build_register(parse_register_rows(raw_html), limit_days, future_days)
