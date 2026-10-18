"""Config flow for the Dongfeng eπ integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow

try:  # ConfigFlowResult only exists on HA >= 2024.7
    from homeassistant.config_entries import ConfigFlowResult
except ImportError:  # pragma: no cover - older HA
    from typing import Any

    ConfigFlowResult = Any

from .const import (
    CONF_APP_ID,
    CONF_DEVICE_ID,
    CONF_ENABLE_CTRL,
    CONF_HOST,
    CONF_MOCK,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_VIN,
    DEFAULT_APP_ID,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("use_demo", default=True): bool,
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_VIN, default=""): str,
        vol.Optional(CONF_TOKEN, default=""): str,
        vol.Optional(CONF_APP_ID, default=DEFAULT_APP_ID): str,
        vol.Optional(CONF_DEVICE_ID, default="homeassistant"): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=15, max=3600)
        ),
        vol.Optional(CONF_ENABLE_CTRL, default=True): bool,
    }
)


class DfpConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 东风奕派车辆状态."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("use_demo"):
                # demo mode: render the dashboard from built-in mock data,
                # no VIN / token required
                data = dict(user_input)
                data[CONF_VIN] = "MOCKDEMO00000001"
                data[CONF_TOKEN] = "mock"
                data[CONF_MOCK] = True
                await self.async_set_unique_id("mockdemo00000001")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="奕派 Demo（模拟数据）", data=data
                )
            if not user_input.get(CONF_VIN):
                errors[CONF_VIN] = "missing_vin"
            elif not user_input.get(CONF_TOKEN):
                errors[CONF_TOKEN] = "missing_token"
            else:
                vin = user_input[CONF_VIN]
                await self.async_set_unique_id(vin.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"奕派 {vin[-6:]}",
                    data=user_input,
                )
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_demo(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create an entry that renders with mock vehicle data."""
        if user_input is not None:
            return self.async_create_entry(
                title="奕派 Demo（模拟数据）",
                data={
                    CONF_HOST: DEFAULT_HOST,
                    CONF_VIN: "MOCKDEMO00000001",
                    CONF_TOKEN: "mock",
                    CONF_APP_ID: DEFAULT_APP_ID,
                    CONF_DEVICE_ID: "homeassistant",
                    CONF_SCAN_INTERVAL: 30,
                    CONF_MOCK: True,
                    CONF_ENABLE_CTRL: True,
                },
            )
        return self.async_show_form(
            step_id="demo",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "confirm_demo",
                        description={"suggested_value": "使用内置模拟车辆数据创建演示实例"},
                    ): bool
                }
            ),
        )
