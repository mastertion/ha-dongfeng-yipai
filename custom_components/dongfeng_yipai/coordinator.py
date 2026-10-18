"""Data coordinator for the Dongfeng eπ integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DfpApiError, DfpApiClient

_LOGGER = logging.getLogger(__name__)


class DfpDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: DfpApiClient,
                 scan_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="dongfeng_yipai",
            update_interval=timedelta(seconds=max(15, scan_interval)),
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            data = await self.client.get_vehicle_status()
        except DfpApiError as err:
            raise UpdateFailed(f"车辆状态获取失败: {err}") from err
        _LOGGER.debug("vehicle status: %s", data)
        return data


def dig(data: dict, path: str, default=None):
    """Safe nested lookup: dig(d, 'airCondition.acStatus')."""
    cur = data
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return default if cur is None else cur
