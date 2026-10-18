"""Support for Dongfeng eπ (dfmc.dfpv.sapp) vehicles."""
from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .api import DfpApiClient
from .const import (
    CONF_APP_ID,
    CONF_DEVICE_ID,
    CONF_ENABLE_CTRL,
    CONF_MOCK,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_VIN,
    DEFAULT_APP_ID,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import DfpDataUpdateCoordinator
from .mock_data import MOCK_VEHICLE_STATUS

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
]

# ---- configuration.yaml support -------------------------------------------------
# dongfeng_yipai:
#   use_demo: true          # 演示模式（内置模拟数据）
# 或多车辆列表:
# dongfeng_yipai:
#   - vin: "LFV..."
#     token: "eyJ..."
#     host: https://dfypappgw-pros.dfiov.com.cn
_VEHICLE_SCHEMA = vol.Schema(
    {
        vol.Optional("use_demo", default=False): bool,
        vol.Optional(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Optional(CONF_VIN, default=""): str,
        vol.Optional(CONF_TOKEN, default=""): str,
        vol.Optional(CONF_APP_ID, default=DEFAULT_APP_ID): str,
        vol.Optional(CONF_DEVICE_ID, default="homeassistant"): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=15, max=3600)
        ),
        vol.Optional(CONF_ENABLE_CTRL, default=True): bool,
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Any(_VEHICLE_SCHEMA, [_VEHICLE_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Create config entries from configuration.yaml via the import flow."""
    cfg = config.get(DOMAIN)
    if not cfg:
        return True
    vehicles = cfg if isinstance(cfg, list) else [cfg]
    for vehicle in vehicles:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=dict(vehicle)
            )
        )
    return True


class _MockClient:
    """Returns canned payloads so the dashboard can be evaluated offline."""

    def __init__(self) -> None:
        self._charging = True

    async def get_vehicle_status(self) -> dict:
        data = dict(MOCK_VEHICLE_STATUS["data"])
        data["chargingStatus"] = 1 if self._charging else 0
        return data

    async def charge_start(self) -> dict:
        self._charging = True
        return {"code": "000000"}

    async def charge_stop(self) -> dict:
        self._charging = False
        return {"code": "000000"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data.get(CONF_HOST)
    token = entry.data.get(CONF_TOKEN, "")
    vin = entry.data.get(CONF_VIN, "")
    app_id = entry.data.get(CONF_APP_ID) or "dfpv-sapp-android"
    device_id = entry.data.get(CONF_DEVICE_ID) or "homeassistant"
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, 60)
    mock = entry.data.get(CONF_MOCK, False)

    if mock:
        client = _MockClient()
    else:
        session = aiohttp.ClientSession(
            headers={"User-Agent": "dongfeng-yipai-ha-bridge"}
        )
        client = DfpApiClient(session, host, token, vin, app_id, device_id)
        entry.async_on_unload(session.close)

    coordinator = DfpDataUpdateCoordinator(hass, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "vin": vin or "mock-vin-0001",
        "enable_ctrl": entry.data.get(CONF_ENABLE_CTRL, True),
    }

    try:  # batch API added in HA 2023.9; fall back on older cores
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except AttributeError:
        for platform in PLATFORMS:
            await hass.config_entries.async_forward_entry_setup(entry, platform)

    # auto-register the built-in dashboard panel (no manual Lovelace needed)
    try:
        from .panel import async_setup_panel

        await async_setup_panel(hass, entry)
    except Exception:  # pragma: no cover - panel is best-effort
        _LOGGER.exception("奕派仪表盘面板注册失败（实体不受影响）")

    # register the Xiaomi-style custom cards into Lovelace resources
    try:
        from .cards import ensure_cards_resources

        await ensure_cards_resources(hass)
    except Exception:  # pragma: no cover
        _LOGGER.debug("奕派卡片资源注册失败", exc_info=True)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        try:
            from .panel import async_remove_panel_entry

            await async_remove_panel_entry(hass, entry)
        except Exception:  # pragma: no cover
            _LOGGER.debug("奕派面板移除失败", exc_info=True)
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
