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


def _diag_headers(headers) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() in _DIAG_RESPONSE_HEADERS}


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
                body = (await response.text())[:500]
                raise AxiosAuthError(
                    f"Login rejected (HTTP {response.status}); body={body!r}"
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
    async def _raw_action(self, action: str, require_json: bool = True) -> str:
        """One APP_Ajax_Get.aspx call, without the logged_in/retry logic."""
        headers = self._ajax_headers()
        async with self._session.get(
            f"{BASE_URL}{AJAX_PATH}",
            params={"Action": action, "_": str(int(time.time() * 1000))},
            headers=headers,
            timeout=self._timeout,
        ) as response:
            if response.status >= 400:
                body = (await response.text())[:500]
                raise AxiosApiError(
                    f"{action} returned HTTP {response.status}: body={body!r}; "
                    f"response_headers={_diag_headers(response.headers)}"
                )
            raw_body = await response.text()
            try:
                payload: dict[str, Any] = json.loads(raw_body)
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

    async def async_get_data(self) -> dict[str, Any]:
        communications_html = await self._action("FAMILY_COMUNICAZIONI")
        absences_html = await self._action("FAMILY_ASSENZE")
        register_html = await self._action("FAMILY_REGISTRO_CLASSE")
        return {
            "communications": parse_communications(
                communications_html, self._communications_limit
            ),
            "absences": parse_absences(absences_html),
            "register": parse_register(register_html, self._register_days),
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
        # solo l'elenco è limitato.
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
        cutoff = datetime.now().astimezone().date() - timedelta(days=limit_days)
        recent = [(d, row) for d, row in parsed if d >= cutoff]
        recent.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in recent]
    _LOGGER.warning(
        "Axios register: could not parse all dates (example: %r); "
        "falling back to the first %d rows",
        days[0]["date"], limit_days,
    )
    return days[:limit_days]


def parse_register(raw_html: str, limit_days: int = DEFAULT_REGISTER_DAYS) -> dict[str, Any]:
    soup = BeautifulSoup(raw_html, "html.parser")
    days: list[dict[str, Any]] = []
    table = soup.select_one("#table-rcla")
    if table:
        for row in table.select("tbody tr"):
            cells = row.find_all("td")
            if len(cells) < 7:
                continue
            days.append({
                "date": _text(cells[0]),
                "topics": _text(cells[1]),
                "homework": _text(cells[2]),
                "tests": _text(cells[3]),
                "absences": _text(cells[4]),
                "annotations": _text(cells[5]),
                "disciplinary_notes": _text(cells[6]),
            })

    total_rows = len(days)
    days = _limit_recent_days(days, limit_days)
    _LOGGER.debug(
        "Axios register: kept %d of %d rows (last %d days)",
        len(days), total_rows, limit_days,
    )

    homework = [d for d in days if d["homework"] or d["tests"]]
    annotations = [d for d in days if d["annotations"]]
    notes = [d for d in days if d["disciplinary_notes"]]
    return {
        "window_days": limit_days,
        "days": days,
        "homework_count": len(homework),
        "annotation_count": len(annotations),
        "disciplinary_note_count": len(notes),
        "homework": homework,
        "annotations": annotations,
        "disciplinary_notes": notes,
    }
