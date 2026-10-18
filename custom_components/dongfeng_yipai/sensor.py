"""Sensors for the Dongfeng eπ integration.

Field names come from the app's JSON payload shape (classes.dex string pool)
and from the in-vehicle ADS protobuf definitions:
  powerSocStatus / chargingStatus / batteryPackChrgDchrgPower /
  batteryPackChrgDchrgTimeLength / acCabinTemperature / tyrePressure ...
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)

try:  # HA 2024.4+ 将电功率单位枚举更名为 UnitOfPower
    from homeassistant.const import UnitOfPower as _UnitOfPower
except ImportError:  # 兼容更旧版本
    from homeassistant.const import UnitOfElectricPower as _UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DfpDataUpdateCoordinator, dig
from .entity import DfpEntity


def _t(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return None


def _kw(d: dict):
    watts = dig(d, "batteryPackChrgDchrgPower")
    return None if watts is None else round(watts / 1000.0, 2)


@dataclass(frozen=True, kw_only=True)
class DfpSensorDescription(SensorEntityDescription):
    """`lookup` pulls the value out of the TSP payload."""

    lookup: Callable[[dict], object] | None = None


DESCRIPTIONS: tuple[DfpSensorDescription, ...] = (
    DfpSensorDescription(
        key="powerSocStatus",
        translation_key="battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DfpSensorDescription(
        key="enduranceMileage",
        translation_key="remaining_range",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:car-electric",
    ),
    DfpSensorDescription(
        key="totalMileage",
        translation_key="total_mileage",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:road-variant",
    ),
    DfpSensorDescription(
        key="charge_power_kw",
        translation_key="charge_power",
        lookup=_kw,
        native_unit_of_measurement=_UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash",
    ),
    DfpSensorDescription(
        key="batteryPackChrgDchrgTimeLength",
        translation_key="charge_remaining_time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-sync",
    ),
    DfpSensorDescription(
        key="acCabinTemperature",
        translation_key="cabin_temperature",
        lookup=lambda d: dig(
            d, "airCondition.acCabinTemperature", dig(d, "acCabinTemperature")
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
    ),
    DfpSensorDescription(
        key="outTemperature",
        translation_key="outside_temperature",
        lookup=lambda d: dig(
            d, "airCondition.outTemperature", dig(d, "outTemperature")
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer-outdoor",
    ),
    DfpSensorDescription(
        key="speed",
        translation_key="speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer-medium",
    ),
    DfpSensorDescription(
        key="tyre_left_front",
        translation_key="tyre_pressure_lf",
        lookup=lambda d: dig(d, "tyrePressure.leftFront"),
        native_unit_of_measurement="kPa",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:car-tire-alert",
    ),
    DfpSensorDescription(
        key="tyre_right_front",
        translation_key="tyre_pressure_rf",
        lookup=lambda d: dig(d, "tyrePressure.rightFront"),
        native_unit_of_measurement="kPa",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:car-tire-alert",
    ),
    DfpSensorDescription(
        key="tyre_left_rear",
        translation_key="tyre_pressure_lr",
        lookup=lambda d: dig(d, "tyrePressure.leftRear"),
        native_unit_of_measurement="kPa",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:car-tire-alert",
    ),
    DfpSensorDescription(
        key="tyre_right_rear",
        translation_key="tyre_pressure_rr",
        lookup=lambda d: dig(d, "tyrePressure.rightRear"),
        native_unit_of_measurement="kPa",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:car-tire-alert",
    ),
    DfpSensorDescription(
        key="updateTime",
        translation_key="last_report",
        lookup=lambda d: _t(dig(d, "updateTime")),
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    info = hass.data[DOMAIN][entry.entry_id]
    coord: DfpDataUpdateCoordinator = info["coordinator"]
    async_add_entities(
        DfpSensor(coord, info["vin"], description) for description in DESCRIPTIONS
    )


class DfpSensor(DfpEntity, SensorEntity):
    def __init__(self, coord, vin, description: DfpSensorDescription) -> None:
        super().__init__(coord, vin, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        lookup = self.entity_description.lookup
        if lookup is not None:
            return lookup(data)
        return dig(data, self.entity_description.key)
