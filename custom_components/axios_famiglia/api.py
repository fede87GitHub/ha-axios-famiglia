from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import functools
import html as html_lib
import json
import logging
import re
import time
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout
from bs4 import BeautifulSoup

from .const import (
    AJAX_PATH,
    BASE_URL,
    DASHBOARD_INIT_ACTIONS,
    DASHBOARD_PATH_HINT,
    DEFAULT_COMMUNICATIONS_LIMIT,
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
WEEK_REQUEST_CONTENT_TYPE = "application/x-www-form-urlencoded; charset=UTF-8"
# Le settimane piu' vecchie della precedente cambiano di rado: si rileggono ogni 6 ore.
# La settimana precedente e quella corrente si leggono a ogni aggiornamento.
OLD_WEEK_CACHE_SECONDS = 6 * 60 * 60


def _diag_headers(headers) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() in _DIAG_RESPONSE_HEADERS}


def _today() -> date:
    return datetime.now().astimezone().date()


class AxiosApiError(Exception):
    """Base Axios API error."""


class AxiosAuthError(AxiosApiError):
    """Authentication failed (wrong credentials)."""


class AxiosRvtError(AxiosApiError):
    """Login succeeded but the anti-CSRF token could not be found."""


class AxiosInitSequenceError(AxiosApiError):
    """Dashboard-initialization sequence (HeaderLoad/FooterLoad/DashboardLoad) failed."""


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
        communications_limit: int = DEFAULT_COMMUNICATIONS_LIMIT,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        self._session = session
        self._credentials = credentials
        self._register_days = register_days
        self._communications_limit = communications_limit
        self._timeout = ClientTimeout(total=request_timeout)
        self._logged_in = False
        self._dashboard_url: str | None = None
        self._rvt: str | None = None
        # monday of the week -> (time of the reading, rows)
        self._week_cache: dict[date, tuple[float, list[dict[str, Any]]]] = {}
        self._weeks_warned = False

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

        for init_action in DASHBOARD_INIT_ACTIONS:
            try:
                await self._raw_action(init_action, require_json=False)
            except AxiosApiError as err:
                _LOGGER.error(
                    "Axios login: dashboard init call '%s' FAILED: %s", init_action, err,
                )
                raise AxiosInitSequenceError(
                    f"Dashboard initialization call '{init_action}' failed: {err}"
                ) from err
            _LOGGER.debug("Axios login: dashboard init call '%s' completed", init_action)

        self._logged_in = True

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
        given (used to read a past register week). The browser's POST has NO "_" parameter.
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
                _LOGGER.debug(
                    "Axios action %s: response was not JSON (content-type=%s). "
                    "Raw body (first 500 chars): %r",
                    action, response.headers.get("Content-Type"), raw_body[:500],
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
            # Session may have expired: retry once after a fresh login.
            self._logged_in = False
            await self.login()
            return await self._raw_action(action)

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

    async def _read_previous_weeks(self) -> tuple[list[dict[str, Any]], bool]:
        """Rows of the previous weeks that fall in the reading window.

        Returns (rows, complete). A week that cannot be read never breaks the update:
        its last known rows are used if there are any, otherwise it is skipped.
        """
        today = _today()
        this_monday = today - timedelta(days=today.weekday())
        mondays = past_week_mondays(today, self._register_days)
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
        communications_html = await self._action("FAMILY_COMUNICAZIONI")
        absences_html = await self._action("FAMILY_ASSENZE")
        # The current week comes from the call that is known to work; the previous
        # weeks (if any are needed) are added after it.
        register_html = await self._action(REGISTER_ACTION)
        current_rows = parse_register_rows(register_html)
        older_rows, complete = await self._read_previous_weeks()
        rows = merge_register_rows(current_rows, older_rows)
        return {
            "communications": parse_communications(
                communications_html, self._communications_limit
            ),
            "absences": parse_absences(absences_html),
            "register": build_register(rows, self._register_days, partial=not complete),
            "updated_at": datetime.now().astimezone().isoformat(),
        }


def _text(node: Any) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


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


def _limit_recent_days(days: list[dict[str, Any]], limit_days: int) -> list[dict[str, Any]]:
    """Keep only the register rows of the last `limit_days` days (newest first).

    If a date cannot be parsed, fall back to the first `limit_days` rows.
    """
    if limit_days <= 0 or not days:
        return days
    parsed = [(_parse_date(day["date"]), day) for day in days]
    if all(day_date is not None for day_date, _ in parsed):
        cutoff = _today() - timedelta(days=limit_days)
        recent = [(d, row) for d, row in parsed if d >= cutoff]
        recent.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in recent]
    _LOGGER.warning(
        "Axios register: could not parse all dates (example: %r); "
        "falling back to the first %d rows",
        days[0]["date"], limit_days,
    )
    return days[:limit_days]


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
    rows: list[dict[str, Any]], limit_days: int = DEFAULT_REGISTER_DAYS, partial: bool = False
) -> dict[str, Any]:
    total_rows = len(rows)
    days = _limit_recent_days(rows, limit_days)
    _LOGGER.debug(
        "Axios register: kept %d of %d rows (last %d days)",
        len(days), total_rows, limit_days,
    )

    homework = [d for d in days if d["homework"] or d["tests"]]
    annotations = [d for d in days if d["annotations"]]
    notes = [d for d in days if d["disciplinary_notes"]]
    return {
        "window_days": limit_days,
        "partial": partial,
        "days": days,
        "homework_count": len(homework),
        "annotation_count": len(annotations),
        "disciplinary_note_count": len(notes),
        "homework": homework,
        "annotations": annotations,
        "disciplinary_notes": notes,
    }


def parse_register(raw_html: str, limit_days: int = DEFAULT_REGISTER_DAYS) -> dict[str, Any]:
    """Single page (the current week): kept for compatibility."""
    return build_register(parse_register_rows(raw_html), limit_days)
