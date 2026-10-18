"""Button for the Dongfeng eπ integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DfpEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    info = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DfpRefreshButton(info["coordinator"], info["vin"])])


class DfpRefreshButton(DfpEntity, ButtonEntity):
    """Force an immediate poll of the TSP cloud status."""

    _attr_translation_key = "refresh"
    _attr_icon = "mdi:cloud-sync"

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
