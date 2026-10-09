from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import AxiosFamigliaCoordinator
from .entity import AxiosEntity
from .items import (
    EVENT_NEW_ABSENCE,
    EVENT_NEW_ANNOTATION,
    EVENT_NEW_COMMUNICATION,
    EVENT_NEW_HOMEWORK,
    EVENT_NEW_NOTE,
    EVENT_NEW_TEST,
    calendar_entries,
)


@dataclass(frozen=True)
class CalendarSpec:
    key: str  # suffisso dell'entity_id e translation_key
    icon: str
    types: frozenset[str]  # tipi di voce mostrati in questo calendario


CALENDARS: tuple[CalendarSpec, ...] = (
    CalendarSpec("absences", "mdi:calendar-remove", frozenset({EVENT_NEW_ABSENCE})),
    CalendarSpec(
        "homework", "mdi:notebook-edit", frozenset({EVENT_NEW_HOMEWORK, EVENT_NEW_TEST})
    ),
    CalendarSpec(
        "annotations", "mdi:note-text", frozenset({EVENT_NEW_ANNOTATION, EVENT_NEW_NOTE})
    ),
    CalendarSpec("communications", "mdi:bullhorn", frozenset({EVENT_NEW_COMMUNICATION})),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AxiosFamigliaCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Rimuove il calendario unico della v1.1.0 (ora sostituito da quelli separati)
    registry = er.async_get(hass)
    legacy = registry.async_get_entity_id("calendar", DOMAIN, f"{entry.entry_id}_register")
    if legacy:
        registry.async_remove(legacy)

    async_add_entities(AxiosCalendar(coordinator, entry, spec) for spec in CALENDARS)


class AxiosCalendar(AxiosEntity, CalendarEntity):
    """Un calendario del registro, limitato ad alcuni tipi di voce."""

    def __init__(
        self, coordinator: AxiosFamigliaCoordinator, entry: ConfigEntry, spec: CalendarSpec
    ) -> None:
        super().__init__(coordinator, entry, "calendar", spec.key)
        self._spec = spec
        self._attr_translation_key = spec.key
        self._attr_icon = spec.icon

    def _calendar_events(self) -> list[CalendarEvent]:
        language = self.coordinator.hass.config.language
        return [
            CalendarEvent(
                start=entry["start"],
                end=entry["end"],
                summary=entry["summary"],
                description=entry["description"],
                uid=entry["uid"],
            )
            for entry in calendar_entries(
                self.coordinator.data or {}, language, self._spec.types
            )
        ]

    @property
    def event(self) -> CalendarEvent | None:
        """Evento in corso oggi o, in mancanza, il prossimo."""
        today = dt_util.now().date()
        upcoming = [e for e in self._calendar_events() if e.end > today]
        upcoming.sort(key=lambda e: e.start)
        return upcoming[0] if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        events = [
            e
            for e in self._calendar_events()
            if dt_util.start_of_local_day(e.start) < end_date
            and dt_util.start_of_local_day(e.end) > start_date
        ]
        events.sort(key=lambda e: e.start)
        return events
