"""HTTP client for the Dongfeng eπ (dfmc.dfpv.sapp) TSP gateway.

Endpoints were recovered from the APK's classes.dex string pool.
Auth model: the app obtains a bearer token via auth/v2/token against
idp-prd.dfiov.com.cn / the app gateway.  Reproducing the login + request
signature inside Home Assistant is out of scope (the APK is hardened with
iJianGuo/secneo and the config assets are encrypted), so this client takes
a token that you copy from a packet capture of the official app.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from .const import (
    CLIENT_VERSION,
    PATH_CHARGE_START,
    PATH_CHARGE_STOP,
    PATH_VEHICLE_STATUS,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

_OK_CODES = {"0", "000000", "200", "SUCCESS", "success", 0, 200}


class DfpApiError(Exception):
    """Raised when the gateway returns an error or an unexpected payload."""


class DfpApiClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        token: str,
        vin: str,
        app_id: str,
        device_id: str,
    ) -> None:
        self._session = session
        self._host = host.rstrip("/")
        self._token = token.strip()
        self._vin = vin.strip()
        self._headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {self._token}"
            if not self._token.lower().startswith(("bearer", "token"))
            else self._token,
            "X-App-Id": app_id,
            "X-Device-Id": device_id,
            "X-Client-Version": CLIENT_VERSION,
            "X-Client-Model": "HA-bridge",
            "X-Auth-Token": self._token,
        }

    async def _request(
        self, method: str, path: str, *, params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict[str, Any]:
        url = f"{self._host}{path}"
        try:
            async with self._session.request(
                method, url, headers=self._headers,
                params=params, json=json_body, timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()
                if resp.status in (401, 403):
                    raise DfpApiError(
                        f"鉴权失败 HTTP {resp.status}：token 可能已过期，请重新抓包获取"
                    )
                if resp.status >= 400:
                    raise DfpApiError(f"HTTP {resp.status}: {text[:200]}")
        except aiohttp.ClientError as err:
            raise DfpApiError(f"网络错误: {err}") from err

        try:
            payload = json.loads(text)
        except ValueError as err:
            raise DfpApiError("网关返回的不是 JSON（可能被 WAF/签名校验拦截）") from err

        if isinstance(payload, dict):
            code = payload.get("code", payload.get("resultCode", payload.get("status")))
            if code is not None and str(code).upper() not in {str(c).upper() for c in _OK_CODES}:
                msg = payload.get("msg") or payload.get("message") or ""
                raise DfpApiError(f"业务错误 code={code} msg={msg}")
        return payload

    @staticmethod
    def _unwrap(payload: dict) -> dict:
        data = payload.get("data", payload)
        return data if isinstance(data, dict) else {}

    async def get_vehicle_status(self) -> dict[str, Any]:
        """Poll the same endpoint the official app uses.

        The exact query-parameter name for the VIN was not recoverable from
        the hardened DEX, so we send a few common aliases; the gateway
        typically ignores the extra ones.  Adjust in api.py if your capture
        shows a different name.
        """
        payload = await self._request(
            "GET", PATH_VEHICLE_STATUS,
            params={"vin": self._vin, "vehicleId": self._vin, "vehicleCode": self._vin},
        )
        return self._unwrap(payload)

    async def charge_start(self) -> dict[str, Any]:
        payload = await self._request(
            "POST", PATH_CHARGE_START, json_body={"vin": self._vin}
        )
        return self._unwrap(payload)

    async def charge_stop(self) -> dict[str, Any]:
        payload = await self._request(
            "POST", PATH_CHARGE_STOP, json_body={"vin": self._vin}
        )
        return self._unwrap(payload)
