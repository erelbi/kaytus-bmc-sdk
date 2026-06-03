"""Syslog service configuration.

Real payload from KR2280-X3 / BMC 4.35.00:
  SyslogServers[].MemberId  : 0-3
  SyslogServers[].Enabled   : "Enable" | "Disable"  (string, not bool)
  SyslogServers[].Logtype   : "Audit+IDL" | "SEL" | ...
  ServiceSyslogEnable       : "RemoteEnable"
  TransmissionProtocol      : "UDP" | "TCP" | "TLS"
  AlarmSeverity             : "Warning" | "Critical" | "Info"
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import KaytusClient

_SYSLOG = "/redfish/v1/Managers/1/SyslogService/"

LOG_TYPES  = ["Audit", "IDL", "Audit+IDL", "SEL", "Audit+SEL", "IDL+SEL", "Audit+IDL+SEL"]
PROTOCOLS  = ["UDP", "TCP", "TLS"]
SEVERITIES = ["Critical", "Warning", "Info"]
TAG_OPTIONS = ["HostName", "IP"]

_READ_ONLY = {
    "@odata.id", "@odata.type", "Actions", "Description",
    "Id", "Name", "ServiceEnabled", "AuthenticationType",
}


class SyslogModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    def info(self) -> dict:
        """Full SyslogService resource."""
        return self._c.get(_SYSLOG)

    def summary(self) -> dict:
        """Concise syslog status."""
        d = self.info()
        return {
            "enabled":        d.get("ServiceEnabled"),
            "protocol":       d.get("TransmissionProtocol"),
            "tag":            d.get("ServiceSyslogTag"),
            "severity":       d.get("AlarmSeverity"),
            "active_servers": [
                s for s in d.get("SyslogServers", []) if s.get("Enabled") == "Enable"
            ],
        }

    def set_server(
        self,
        index: int,
        address: str,
        port: int = 514,
        *,
        protocol: str = "UDP",
        log_type: str = "Audit+IDL",
        severity: str = "Warning",
        tag: str = "HostName",
    ) -> dict:
        """
        Enable and configure a syslog server slot (index 0-3).
        Reads current config, updates only the given slot, patches back.
        """
        if index not in range(4):
            raise ValueError("Server index must be 0-3")
        if protocol not in PROTOCOLS:
            raise ValueError(f"protocol must be one of {PROTOCOLS}")
        if severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES}")
        if log_type not in LOG_TYPES:
            raise ValueError(f"log_type must be one of {LOG_TYPES}")

        body, etag = self._c.get_with_etag(_SYSLOG)
        for key in _READ_ONLY:
            body.pop(key, None)

        servers = body.get("SyslogServers", [])
        slot = next((s for s in servers if s.get("MemberId") == index), None)
        if slot is None:
            raise ValueError(f"Syslog slot {index} not found on this BMC")

        slot["Address"] = address
        slot["Port"]    = port
        slot["Enabled"] = "Enable"
        slot["Logtype"] = log_type

        body["ServiceSyslogEnable"]  = "RemoteEnable"
        body["ServiceSyslogTag"]     = tag
        body["TransmissionProtocol"] = protocol
        body["AlarmSeverity"]        = severity
        body["SyslogServers"]        = servers

        return self._c.patch(_SYSLOG, body, etag=etag)

    def disable_server(self, index: int) -> dict:
        """Disable a syslog server slot."""
        if index not in range(4):
            raise ValueError("Server index must be 0-3")
        body, etag = self._c.get_with_etag(_SYSLOG)
        for key in _READ_ONLY:
            body.pop(key, None)
        servers = body.get("SyslogServers", [])
        slot = next((s for s in servers if s.get("MemberId") == index), None)
        if slot:
            slot["Enabled"] = "Disable"
            body["SyslogServers"] = servers
        return self._c.patch(_SYSLOG, body, etag=etag)

    def test(self) -> dict:
        """Send a test syslog event."""
        return self._c.post(f"{_SYSLOG}Actions/SyslogService.SubmitTestEvent/")
