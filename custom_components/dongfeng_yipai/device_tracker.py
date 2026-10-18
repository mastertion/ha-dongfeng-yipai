"""Device tracker (vehicle GPS position) for the Dongfeng eπ integration."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType

try:  # HA 2025.x exposes TrackerEntity at the package root
    from homeassistant.components.device_tracker import TrackerEntity
except ImportError:  # pragma: no cover - older HA
    from homeassistant.components.device_tracker.config_entry import TrackerEntity

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import dig
from .entity import DfpEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    info = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DfpVehicleLocation(info["coordinator"], info["vin"])])


class DfpVehicleLocation(DfpEntity, TrackerEntity):
    """GPS tracker.  Uses TrackerEntity (not ScannerEntity, whose
    is_connected raises NotImplementedError and crashed entity creation)."""

    _attr_translation_key = "location"
    _attr_icon = "mdi:crosshairs-gps"

    def __init__(self, coord, vin) -> None:
        super().__init__(coord, vin, "location")

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self):
        lat = dig(self.coordinator.data or {}, "location.latitude")
        return None if lat in (None, 0, "") else float(lat)

    @property
    def longitude(self):
        lon = dig(self.coordinator.data or {}, "location.longitude")
        return None if lon in (None, 0, "") else float(lon)

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "position_time": dig(data, "location.positionTime"),
            "vin": self._vin,
        }
