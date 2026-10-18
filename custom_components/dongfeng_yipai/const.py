"""Constants for the 东风奕派 (Dongfeng eπ / Yipai) integration."""
from __future__ import annotations

DOMAIN = "dongfeng_yipai"
PLATFORMS = ["sensor", "binary_sensor", "switch", "button", "device_tracker"]

# ---- config keys ----
CONF_HOST = "host"
CONF_TOKEN = "token"
CONF_VIN = "vin"
CONF_APP_ID = "app_id"
CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MOCK = "mock_mode"
CONF_ENABLE_CTRL = "enable_charge_control"

DEFAULT_HOST = "https://dfypappgw-pros.dfiov.com.cn"
DEFAULT_APP_ID = "dfpv-sapp-android"
DEFAULT_SCAN_INTERVAL = 60
CLIENT_VERSION = "2.1.9"
USER_AGENT = (
    "dfmc-dfpv-sapp/2.1.9 (Android; okhttp/4) dongfeng-yipai-ha-bridge/0.1"
)

# ---- endpoints recovered from com.dfmc.dfpv.sapp classes.dex ----
PATH_VEHICLE_STATUS = "/msvehiclestatus/vehiclestatus/v3/vehicleStatus"
PATH_VEHICLE_STATUS_POINT = "/msvehiclestatus/vehiclestatus/v3/vehicleStatusWithPoint"
PATH_CHARGE_START = "/mscharge/charging/start"
PATH_CHARGE_STOP = "/mscharge/charging/stop"

# MQTT topic seen in the app (for reference / future realtime mode)
MQTT_TOPIC_VEHICLE_REPORT = "msvehiclestatus/vehiclereport/travelAndCharge"

ICON_BRAKES = "mdi:car-brake-fluid-level"
