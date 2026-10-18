"""Binary sensors for the Dongfeng eπ integration.

Semantics follow the ADS protobuf notes recovered from the APK:
  chargingStatus: 0未连接未充电/1充电中/2完成/3故障/4连接未充电
  chargingPortStatus: 0关/1开 ; rearViewMirrorStatus: 0折叠/1展开
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DfpDataUpdateCoordinator, dig
from .entity import DfpEntity


def _any_door_open(d: dict) -> bool:
    doors = dig(d, "doorStatus", {}) or {}
    if not isinstance(doors, dict):
        return False
    for v in doors.values():
        try:
            if int(v) == 1:
                return True
        except (TypeError, ValueError):
            continue
    return False


@dataclass(frozen=True, kw_only=True)
class DfpBinaryDescription(BinarySensorEntityDescription):
    lookup: Callable[[dict], object] | None = None


DESCRIPTIONS: tuple[DfpBinaryDescription, ...] = (
    DfpBinaryDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        lookup=lambda d: dig(d, "chargingStatus", 0) == 1,
    ),
    DfpBinaryDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        lookup=lambda d: int(dig(d, "online", 0) or 0) == 1,
    ),
    DfpBinaryDescription(
        key="locked",
        translation_key="locked",
        device_class=BinarySensorDeviceClass.LOCK,
        # app convention: lockStatus 1 = locked
        lookup=lambda d: int(dig(d, "lockStatus", 1) or 0) == 1,
    ),
    DfpBinaryDescription(
        key="doors",
        translation_key="doors_open",
        device_class=BinarySensorDeviceClass.DOOR,
        lookup=_any_door_open,
    ),
    DfpBinaryDescription(
        key="charging_port",
        translation_key="charging_port_open",
        device_class=BinarySensorDeviceClass.DOOR,
        lookup=lambda d: int(dig(d, "chargingPortStatus", 0) or 0) == 1,
    ),
    DfpBinaryDescription(
        key="ac_on",
        translation_key="air_conditioning",
        device_class=BinarySensorDeviceClass.RUNNING,
        lookup=lambda d: int(
            dig(d, "airCondition.acStatus", dig(d, "acStatus", 0)) or 0
        ) == 1,
    ),
    DfpBinaryDescription(
        key="mirror_folded",
        translation_key="mirror_folded",
        device_class=BinarySensorDeviceClass.MOVING,
        lookup=lambda d: int(dig(d, "rearViewMirrorStatus", 1) or 0) == 0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    info = hass.data[DOMAIN][entry.entry_id]
    coord: DfpDataUpdateCoordinator = info["coordinator"]
    async_add_entities(
        DfpBinarySensor(coord, info["vin"], description)
        for description in DESCRIPTIONS
    )


class DfpBinarySensor(DfpEntity, BinarySensorEntity):
    def __init__(self, coord, vin, description: DfpBinaryDescription) -> None:
        super().__init__(coord, vin, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        lookup = self.entity_description.lookup
        if lookup is None:
            return None
        value = lookup(self.coordinator.data or {})
        return None if value is None else bool(value)
