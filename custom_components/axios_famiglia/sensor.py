from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import AxiosFamigliaCoordinator


@dataclass(frozen=True, kw_only=True)
class AxiosSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any]
    attrs_fn: Callable[[dict], dict[str, Any]] | None = None


# I nomi visualizzati vengono da translations/<lingua>.json (entity.sensor.<key>.name)
DESCRIPTIONS: tuple[AxiosSensorDescription, ...] = (
    AxiosSensorDescription(
        key="communications", translation_key="communications", icon="mdi:bullhorn",
        value_fn=lambda d: d["communications"]["total"],
        attrs_fn=lambda d: {
            "non_lette": d["communications"]["unread"],
            "ultima": d["communications"]["latest"],
            "elenco": d["communications"]["items"],
        },
    ),
    AxiosSensorDescription(
        key="communications_unread", translation_key="communications_unread",
        icon="mdi:email-alert",
        value_fn=lambda d: d["communications"]["unread"],
    ),
    AxiosSensorDescription(
        key="absences", translation_key="absences", icon="mdi:calendar-remove",
        value_fn=lambda d: d["absences"]["absences"],
        attrs_fn=lambda d: {
            "ultimo_evento": d["absences"]["latest"],
            "eventi": d["absences"]["events"],
        },
    ),
    AxiosSensorDescription(
        key="late_entries", translation_key="late_entries", icon="mdi:clock-alert",
        value_fn=lambda d: d["absences"]["late_entries"],
    ),
    AxiosSensorDescription(
        key="early_exits", translation_key="early_exits", icon="mdi:exit-run",
        value_fn=lambda d: d["absences"]["early_exits"],
    ),
    AxiosSensorDescription(
        key="absence_percentage", translation_key="absence_percentage",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d["absences"]["percentage"],
    ),
    AxiosSensorDescription(
        key="homework", translation_key="homework", icon="mdi:notebook-edit",
        value_fn=lambda d: d["register"]["homework_count"],
        attrs_fn=lambda d: {
            "giorni_considerati": d["register"]["window_days"],
            "elenco": d["register"]["homework"],
        },
    ),
    AxiosSensorDescription(
        key="annotations", translation_key="annotations", icon="mdi:note-text",
        value_fn=lambda d: d["register"]["annotation_count"],
        attrs_fn=lambda d: {"elenco": d["register"]["annotations"]},
    ),
    AxiosSensorDescription(
        key="disciplinary_notes", translation_key="disciplinary_notes",
        icon="mdi:alert",
        value_fn=lambda d: d["register"]["disciplinary_note_count"],
        attrs_fn=lambda d: {"elenco": d["register"]["disciplinary_notes"]},
    ),
    AxiosSensorDescription(
        key="last_update", translation_key="last_update", icon="mdi:update",
        value_fn=lambda d: d["updated_at"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AxiosFamigliaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AxiosSensor(coordinator, entry, description) for description in DESCRIPTIONS
    )


class AxiosSensor(CoordinatorEntity[AxiosFamigliaCoordinator], SensorEntity):
    entity_description: AxiosSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        student = coordinator.student_name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        # Prefisso fisso e indipendente dalla lingua: sensor.axios_<studente>_<chiave>
        self.entity_id = f"sensor.axios_{slugify(student)}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Axios {student}",
            "manufacturer": "Axios Italia (integrazione non ufficiale)",
            "model": "Registro elettronico Famiglia",
        }

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        if self.entity_description.attrs_fn:
            return self.entity_description.attrs_fn(self.coordinator.data)
        return None