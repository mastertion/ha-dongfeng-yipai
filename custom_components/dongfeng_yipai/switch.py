"""Switch for Dongfeng eπ charge start / stop.

Uses mscharge/charging/start and mscharge/charging/stop, the same paths the
official app calls.  Whether the gateway additionally requires a per-request
signature (the APK is iJianGuo-hardened, so we could not extract the signer)
has to be verified with your own token; enable_charge_control defaults to on
only if you checked it during setup.
"""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DfpDataUpdateCoordinator, dig
from .entity import DfpEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    info = hass.data[DOMAIN][entry.entry_id]
    if not info.get("enable_ctrl", True):
        return
    async_add_entities(
        [DfpChargeSwitch(info["coordinator"], info["vin"], info["client"])]
    )


class DfpChargeSwitch(DfpEntity, SwitchEntity):
    _attr_translation_key = "charge_switch"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coord: DfpDataUpdateCoordinator, vin: str, client) -> None:
        super().__init__(coord, vin, "charge_switch")
        self._client = client

    @property
    def is_on(self) -> bool:
        return dig(self.coordinator.data or {}, "chargingStatus", 0) == 1

    async def async_turn_on(self, **kwargs) -> None:
        await self._client.charge_start()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._client.charge_stop()
        await self.coordinator.async_request_refresh()
