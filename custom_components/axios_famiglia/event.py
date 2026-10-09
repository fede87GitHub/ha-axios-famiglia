from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AxiosFamigliaCoordinator
from .entity import AxiosEntity
from .items import EVENT_TYPES, build_message


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AxiosFamigliaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AxiosNewsEvent(coordinator, entry)])


class AxiosNewsEvent(AxiosEntity, EventEntity):
    """Scatta un evento per ogni novità: comunicazioni, assenze, compiti, verifiche, annotazioni, note."""

    _attr_translation_key = "news"
    _attr_event_types = list(EVENT_TYPES)
    _attr_icon = "mdi:bell-ring"

    def __init__(self, coordinator: AxiosFamigliaCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "event", "news")
        self._last_batch_id = 0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # La prima lettura avviene prima che l'entità esista: se durante lo spegnimento
        # di Home Assistant sono arrivate novità, vanno notificate ora.
        self._fire_pending_events()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._fire_pending_events()
        super()._handle_coordinator_update()

    @callback
    def _fire_pending_events(self) -> None:
        batch_id = self.coordinator.new_events_id
        if batch_id == self._last_batch_id:
            return
        self._last_batch_id = batch_id
        language = self.coordinator.hass.config.language
        for item in self.coordinator.new_events:
            self._trigger_event(
                item["type"],
                {
                    **item["attributes"],
                    "student": self.coordinator.student_name,
                    "message": build_message(item, language),
                },
            )
            # Una scrittura di stato per ogni evento, altrimenti se ne vedrebbe solo l'ultimo
            self.async_write_ha_state()
