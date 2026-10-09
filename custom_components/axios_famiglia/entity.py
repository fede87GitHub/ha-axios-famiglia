from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import AxiosFamigliaCoordinator


class AxiosEntity(CoordinatorEntity[AxiosFamigliaCoordinator]):
    """Base class for the calendar and event entities (same device as the sensors)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AxiosFamigliaCoordinator,
        entry: ConfigEntry,
        platform_domain: str,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        student = coordinator.student_name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        # Prefisso fisso: <dominio>.axios_<studente>_<chiave>
        self.entity_id = f"{platform_domain}.axios_{slugify(student)}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Axios {student}",
            "manufacturer": "Axios Italia (integrazione non ufficiale)",
            "model": "Registro elettronico Famiglia",
        }
