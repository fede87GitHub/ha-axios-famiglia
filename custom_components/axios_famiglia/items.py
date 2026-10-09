"""Pure helpers (no Home Assistant imports) shared by the calendar, event and sensor platforms.

An "item" is one thing that can be new or can be shown on a calendar:
a communication, an absence/late/early-exit entry, a homework, a test,
an annotation or a disciplinary note.

Lesson topics ("argomenti") are NOT items: they are written every day by the
teachers, so they must never trigger a "new item" notification.
"""
from __future__ import annotations

from datetime import date, timedelta
import hashlib
import re
from typing import Any

from .api import _parse_date as _parse_numeric_date

# Quante chiavi "già viste" conservare al massimo (le più vecchie vengono scartate)
MAX_SEEN_ITEMS = 1000

EVENT_NEW_COMMUNICATION = "new_communication"
EVENT_NEW_ABSENCE = "new_absence_event"
EVENT_NEW_HOMEWORK = "new_homework"
EVENT_NEW_TEST = "new_test"
EVENT_NEW_ANNOTATION = "new_annotation"
EVENT_NEW_NOTE = "new_disciplinary_note"

EVENT_TYPES: tuple[str, ...] = (
    EVENT_NEW_COMMUNICATION,
    EVENT_NEW_ABSENCE,
    EVENT_NEW_HOMEWORK,
    EVENT_NEW_TEST,
    EVENT_NEW_ANNOTATION,
    EVENT_NEW_NOTE,
)

# Testi delle notifiche (attributo "message")
_MESSAGES: dict[str, dict[str, str]] = {
    "it": {
        EVENT_NEW_COMMUNICATION: "Nuova comunicazione: {title}",
        EVENT_NEW_ABSENCE: "Nuova voce in Assenze ({date}): {description}",
        EVENT_NEW_HOMEWORK: "Nuovi compiti ({date}): {text}",
        EVENT_NEW_TEST: "Nuova verifica ({date}): {text}",
        EVENT_NEW_ANNOTATION: "Nuova annotazione ({date}): {text}",
        EVENT_NEW_NOTE: "Nuova nota disciplinare ({date}): {text}",
    },
    "en": {
        EVENT_NEW_COMMUNICATION: "New communication: {title}",
        EVENT_NEW_ABSENCE: "New entry in Absences ({date}): {description}",
        EVENT_NEW_HOMEWORK: "New homework ({date}): {text}",
        EVENT_NEW_TEST: "New test ({date}): {text}",
        EVENT_NEW_ANNOTATION: "New annotation ({date}): {text}",
        EVENT_NEW_NOTE: "New disciplinary note ({date}): {text}",
    },
}

# Prefissi dei titoli nei calendari
_CALENDAR_LABELS: dict[str, dict[str, str]] = {
    "it": {
        EVENT_NEW_HOMEWORK: "Compiti",
        EVENT_NEW_TEST: "Verifica",
        EVENT_NEW_ANNOTATION: "Annotazione",
        EVENT_NEW_NOTE: "Nota disciplinare",
        "topics": "Argomenti",
    },
    "en": {
        EVENT_NEW_HOMEWORK: "Homework",
        EVENT_NEW_TEST: "Test",
        EVENT_NEW_ANNOTATION: "Annotation",
        EVENT_NEW_NOTE: "Disciplinary note",
        "topics": "Topics",
    },
}

# Campo del registro -> (tipo di evento, prefisso della chiave)
_REGISTER_FIELDS = (
    ("homework", EVENT_NEW_HOMEWORK, "hw"),
    ("tests", EVENT_NEW_TEST, "test"),
    ("annotations", EVENT_NEW_ANNOTATION, "ann"),
    ("disciplinary_notes", EVENT_NEW_NOTE, "note"),
)

_IT_MONTHS = {
    "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
    "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12,
}
_TEXT_DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-zàèéìòù]+)\.?\s+(\d{4})")


def parse_date(text: str) -> date | None:
    """Parse '09/10/2026', '2026-10-09' and Italian text dates like '05 ottobre 2026'."""
    parsed = _parse_numeric_date(text or "")
    if parsed is not None:
        return parsed
    match = _TEXT_DATE_RE.search(text or "")
    if not match:
        return None
    day, month_name, year = match.groups()
    month = _IT_MONTHS.get(month_name.lower()[:3])
    if month is None:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def _lang(language: str | None) -> str:
    return "it" if (language or "").lower().startswith("it") else "en"


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _short(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def collect_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the coordinator data into a list of items (newest first, as the portal lists them)."""
    items: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    def add(item: dict[str, Any]) -> None:
        if item["key"] in seen_keys:
            return
        seen_keys.add(item["key"])
        items.append(item)

    for comm in (data.get("communications") or {}).get("items", []):
        comm_id = str(comm.get("id") or "")
        if not comm_id:
            continue
        add({
            "key": f"comm:{comm_id}",
            "type": EVENT_NEW_COMMUNICATION,
            "day": parse_date(comm.get("date", "")),
            "text": comm.get("title", ""),
            "attributes": {
                "id": comm_id,
                "title": comm.get("title", ""),
                "author": comm.get("author", ""),
                "date": comm.get("date", ""),
                "category": comm.get("type", ""),
            },
        })

    for event in (data.get("absences") or {}).get("events", []):
        raw_date = event.get("date", "")
        description = event.get("description", "")
        add({
            "key": f"abs:{raw_date}:{_hash(description)}",
            "type": EVENT_NEW_ABSENCE,
            "day": parse_date(raw_date),
            "text": description,
            "attributes": {
                "date": raw_date,
                "description": description,
                "counts": bool(event.get("counts")),
            },
        })

    for day in (data.get("register") or {}).get("days", []):
        raw_date = day.get("date", "")
        parsed = parse_date(raw_date)
        for field, event_type, prefix in _REGISTER_FIELDS:
            text = day.get(field, "")
            if not text:
                continue
            add({
                "key": f"{prefix}:{raw_date}:{_hash(text)}",
                "type": event_type,
                "day": parsed,
                "text": text,
                "attributes": {"date": raw_date, "text": text},
            })

    return items


def split_new(
    seen: list[str] | None,
    items: list[dict[str, Any]],
    max_seen: int = MAX_SEEN_ITEMS,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Compare the current items with the already-seen keys.

    Returns (new_items, updated_seen). `new_items` is ordered oldest first, so
    that the last event fired is the most recent one.
    If `seen` is None (first run ever) nothing is reported as new: the current
    items are just stored, to avoid a flood of notifications on installation.
    """
    if seen is None:
        return [], [item["key"] for item in reversed(items)][-max_seen:]
    seen_set = set(seen)
    new = [item for item in items if item["key"] not in seen_set]
    updated = (seen + [item["key"] for item in reversed(new)])[-max_seen:]
    return list(reversed(new)), updated


def build_message(item: dict[str, Any], language: str | None) -> str:
    template = _MESSAGES[_lang(language)][item["type"]]
    values = {key: _short(str(value), 200) for key, value in item["attributes"].items()}
    try:
        return template.format(**values)
    except KeyError:
        return _short(item["text"], 200)


def calendar_entries(
    data: dict[str, Any],
    language: str | None,
    types: frozenset[str] | set[str] | None = None,
) -> list[dict[str, Any]]:
    """All-day calendar entries for the dated items of the given types (all types if None)."""
    labels = _CALENDAR_LABELS[_lang(language)]
    entries: list[dict[str, Any]] = []
    for item in collect_items(data):
        day: date | None = item["day"]
        if day is None or (types is not None and item["type"] not in types):
            continue
        if item["type"] == EVENT_NEW_ABSENCE:
            summary = _short(item["text"], 80)
            description = item["text"]
        elif item["type"] == EVENT_NEW_COMMUNICATION:
            attrs = item["attributes"]
            header = " - ".join(p for p in (attrs.get("category"), attrs.get("author")) if p)
            summary = _short(item["text"], 80)
            description = "\n".join(p for p in (header, item["text"]) if p)
        else:
            summary = f"{labels[item['type']]}: {_short(item['text'], 80)}"
            description = item["text"]
        entries.append({
            "uid": item["key"],
            "start": day,
            "end": day + timedelta(days=1),
            "summary": summary,
            "description": description,
        })
    return entries


def topic_entries(data: dict[str, Any], language: str | None) -> list[dict[str, Any]]:
    """One all-day calendar entry per register day that has lesson topics."""
    label = _CALENDAR_LABELS[_lang(language)]["topics"]
    entries: list[dict[str, Any]] = []
    seen_uids: set[str] = set()
    for day in (data.get("register") or {}).get("days", []):
        topics = day.get("topics", "")
        raw_date = day.get("date", "")
        parsed = parse_date(raw_date)
        if not topics or parsed is None:
            continue
        uid = f"topics:{raw_date}"
        if uid in seen_uids:
            continue
        seen_uids.add(uid)
        entries.append({
            "uid": uid,
            "start": parsed,
            "end": parsed + timedelta(days=1),
            "summary": f"{label}: {_short(topics, 80)}",
            "description": topics,
        })
    return entries


def latest_topics(data: dict[str, Any]) -> dict[str, Any] | None:
    """The most recent register day that has lesson topics, or None."""
    candidates: list[tuple[date | None, int, dict[str, Any]]] = []
    for index, day in enumerate((data.get("register") or {}).get("days", [])):
        if day.get("topics"):
            candidates.append((parse_date(day.get("date", "")), index, day))
    if not candidates:
        return None
    dated = [c for c in candidates if c[0] is not None]
    if dated:
        parsed, _, day = max(dated, key=lambda c: (c[0], -c[1]))
    else:
        # nessuna data leggibile: il portale elenca di norma dal più recente
        parsed, _, day = candidates[0]
    return {
        "date": day.get("date", ""),
        "iso": parsed.isoformat() if parsed else None,
        "topics": day.get("topics", ""),
    }
