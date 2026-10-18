"""Shared entity base for the Dongfeng eπ integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CLIENT_VERSION, DOMAIN
from .coordinator import DfpDataUpdateCoordinator


class DfpEntity(CoordinatorEntity[DfpDataUpdateCoordinator]):
    """One car = one device; every entity hangs under it.

    suggested_object_id keeps entity ids stable and ASCII
    (sensor.yipai_battery, binary_sensor.yipai_charging, ...), so the
    bundled Lovelace dashboard can reference them directly.  Requires
    Home Assistant >= 2024.7.
    """

    _attr_has_entity_name = True

    def __init__(self, coord: DfpDataUpdateCoordinator, vin: str, key: str) -> None:
        super().__init__(coord)
        self._vin = vin
        self._attr_unique_id = f"{vin}_{key}"
        slug = "yipai_" + key.lower().replace(".", "_")
        self._attr_suggested_object_id = slug
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=f"ePai {vin[-6:]}",
            manufacturer="东风奕派 Dongfeng eπ",
            model="eπ Vehicle (TSP)",
            sw_version=CLIENT_VERSION,
        )
