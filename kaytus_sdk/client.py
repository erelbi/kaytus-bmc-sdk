"""
Kaytus BMC SDK — Redfish HTTP client.
Tested on: KR2280-X3 | BMC 4.35.00 | Redfish 1.18.0
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

import requests
import urllib3

from .exceptions import (
    KaytusAuthError,
    KaytusConnectionError,
    KaytusETagError,
    KaytusHTTPError,
    KaytusNotFoundError,
)
from .modules.system       import SystemModule
from .modules.network      import NetworkModule
from .modules.snmp         import SnmpModule
from .modules.syslog       import SyslogModule
from .modules.logs         import LogsModule
from .modules.accounts     import AccountsModule
from .modules.bios         import BiosModule
from .modules.firmware     import FirmwareModule
from .modules.hardware     import HardwareModule
from .modules.drives       import DrivesModule
from .modules.smtp         import SmtpModule
from .modules.events       import EventsModule
from .modules.virtualmedia import VirtualMediaModule

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)

_SESSION_PATH = "/redfish/v1/SessionService/Sessions"
_DEFAULT_TIMEOUT = 10


class KaytusClient:
    """
    Thread-safe Redfish client for a single Kaytus BMC.

    with KaytusClient("192.168.40.100", "admin", "password") as bmc:
        print(bmc.system.overview())
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 443,
        timeout: int = _DEFAULT_TIMEOUT,
        verify_ssl: bool = False,
    ):
        self.host = host
        self.base_url = f"https://{host}:{port}"
        self._username = username
        self._password = password
        self._timeout = timeout

        self._session = requests.Session()
        self._session.verify = verify_ssl
        self._session_url: Optional[str] = None
        self._lock = threading.Lock()

        self._login()

        self.system       = SystemModule(self)
        self.network      = NetworkModule(self)
        self.snmp         = SnmpModule(self)
        self.syslog       = SyslogModule(self)
        self.logs         = LogsModule(self)
        self.accounts     = AccountsModule(self)
        self.bios         = BiosModule(self)
        self.firmware     = FirmwareModule(self)
        self.hardware     = HardwareModule(self)
        self.drives       = DrivesModule(self)
        self.smtp         = SmtpModule(self)
        self.events       = EventsModule(self)
        self.virtualmedia = VirtualMediaModule(self)

    # ── Public HTTP helpers ───────────────────────────────

    def get(self, path: str) -> dict:
        return self._request("GET", path)

    def patch(self, path: str, data: dict, *, etag: str = "") -> dict:
        headers = {"If-Match": etag} if etag else {}
        return self._request("PATCH", path, json=data, extra_headers=headers)

    def post(self, path: str, data: dict | None = None) -> dict:
        return self._request("POST", path, json=data or {})

    def delete(self, path: str) -> dict:
        return self._request("DELETE", path)

    def get_with_etag(self, path: str) -> tuple[dict, str]:
        """Return (body_dict, etag_string)."""
        resp = self._raw_request("GET", path)
        etag = resp.headers.get("ETag", resp.headers.get("Etag", ""))
        return resp.json(), etag

    def patch_with_etag(self, path: str, data: dict, *, retries: int = 1) -> dict:
        """GET → grab ETag → PATCH. Retries once on 428 stale-ETag."""
        _, etag = self.get_with_etag(path)
        try:
            return self.patch(path, data, etag=etag)
        except KaytusETagError:
            if retries <= 0:
                raise
            _, etag = self.get_with_etag(path)
            return self.patch(path, data, etag=etag)

    # ── Session lifecycle ─────────────────────────────────

    def close(self):
        if self._session_url:
            try:
                self._session.delete(
                    f"{self.base_url}{self._session_url}",
                    timeout=self._timeout,
                )
            except Exception:
                pass
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ── Internal ──────────────────────────────────────────

    def _login(self):
        try:
            resp = self._session.post(
                f"{self.base_url}{_SESSION_PATH}",
                json={"UserName": self._username, "Password": self._password},
                timeout=self._timeout,
            )
        except requests.exceptions.ConnectTimeout as e:
            raise KaytusConnectionError(f"[{self.host}] Connection timed out") from e
        except requests.exceptions.ConnectionError as e:
            raise KaytusConnectionError(f"[{self.host}] Unreachable") from e

        if resp.status_code not in (200, 201):
            raise KaytusAuthError(
                f"[{self.host}] Login failed HTTP {resp.status_code}: {resp.text[:200]}"
            )
        token = resp.headers.get("X-Auth-Token") or resp.json().get("X-Auth-Token")
        if not token:
            raise KaytusAuthError(f"[{self.host}] No X-Auth-Token in login response")

        self._session.headers["X-Auth-Token"] = token
        self._session_url = resp.headers.get("Location", "")
        log.debug(f"[{self.host}] Login OK")

    def _raw_request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        extra_headers: dict | None = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        with self._lock:
            try:
                resp = self._session.request(
                    method, url, json=json,
                    headers=extra_headers or {},
                    timeout=self._timeout,
                )
            except requests.exceptions.ConnectTimeout as e:
                raise KaytusConnectionError(f"[{self.host}] Timeout {method} {path}") from e
            except requests.exceptions.ConnectionError as e:
                raise KaytusConnectionError(f"[{self.host}] Connection error {method} {path}") from e

        if resp.status_code == 401:
            log.info(f"[{self.host}] Token expired — re-login")
            self._login()
            with self._lock:
                resp = self._session.request(
                    method, url, json=json,
                    headers=extra_headers or {},
                    timeout=self._timeout,
                )
        return resp

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        extra_headers: dict | None = None,
    ) -> dict:
        resp = self._raw_request(method, path, json=json, extra_headers=extra_headers)
        return self._handle(resp, method, path)

    def _handle(self, resp: requests.Response, method: str, path: str) -> dict:
        code = resp.status_code

        if code in (200, 201):
            try:
                return resp.json()
            except Exception:
                return {}

        if code == 204:
            return {}

        # Kaytus firmware bug: PATCH/POST returns 400 but actually succeeded
        if code == 400 and method in ("PATCH", "POST"):
            try:
                body = resp.json()
                ext = (
                    body.get("@Message.ExtendedInfo")
                    or body.get("error", {}).get("@Message.ExtendedInfo")
                    or []
                )
                real_errors = [
                    m.get("Message", "")
                    for m in ext
                    if "completed successfully" not in m.get("Message", "")
                ]
                if not real_errors:
                    log.debug(f"[{self.host}] {method} {path} → 400/success firmware bug")
                    return body
            except Exception:
                pass

        if code == 404:
            raise KaytusNotFoundError(code, path)
        if code == 428:
            raise KaytusETagError(f"[{self.host}] Stale ETag on {path}")
        if code in (401, 403):
            raise KaytusAuthError(f"[{self.host}] {code} on {path}")

        raise KaytusHTTPError(code, f"{method} {path} → {resp.text[:300]}")
