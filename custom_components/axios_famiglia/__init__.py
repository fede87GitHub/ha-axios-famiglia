import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import AxiosFamigliaCoordinator
from .panel import async_register_panel, async_remove_panel

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = AxiosFamigliaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Quando l'utente salva le opzioni, l'integrazione si ricarica con i nuovi valori
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    # Il pannello e' un extra: se la registrazione fallisce, sensori e calendari funzionano comunque
    try:
        await async_register_panel(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Axios: could not register the sidebar panel")
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            # Era l'ultimo studente: il pannello non ha piu' niente da mostrare
            async_remove_panel(hass)
    return unloaded
