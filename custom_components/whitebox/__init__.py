"""Integração ISSO Digital White Box."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WhiteboxClient
from .const import CONF_CODE
from .coordinator import WhiteboxCoordinator

PLATFORMS = [Platform.SENSOR]

type WhiteboxConfigEntry = ConfigEntry[WhiteboxCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: WhiteboxConfigEntry) -> bool:
    """Configura um medidor."""
    client = WhiteboxClient(async_get_clientsession(hass), entry.data[CONF_CODE])
    coordinator = WhiteboxCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WhiteboxConfigEntry) -> bool:
    """Remove um medidor."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
