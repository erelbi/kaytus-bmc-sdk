"""SNMP service configuration and trap management."""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..client import KaytusClient

_SNMP = "/redfish/v1/Managers/1/SnmpService"


class SnmpModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    def info(self) -> dict:
        """Full SNMP service resource."""
        return self._c.get(_SNMP)

    def summary(self) -> dict:
        """Concise SNMP status."""
        d = self.info()
        trap = d.get("SnmpTrapNotification", {})
        return {
            "v1_enabled":     d.get("SnmpV1Enable"),
            "v2c_enabled":    d.get("SnmpV2CEnable"),
            "v3_enabled":     d.get("SnmpV3Enable"),
            "read_community":  d.get("ReadOnlyCommunity"),
            "write_community": d.get("ReadWriteCommunity"),
            "trap_version":   trap.get("TrapVersion"),
            "active_trap_servers": [
                s for s in trap.get("TrapServer", []) if s.get("Enabled")
            ],
        }

    def configure(
        self,
        *,
        v1_enable: bool = False,
        v2_enable: bool = True,
        v3_enable: bool = False,
        read_community: Optional[str] = None,
        write_community: Optional[str] = None,
    ) -> dict:
        """
        Configure SNMP version flags and community strings.
        read_community and write_community must differ if both given.
        """
        if read_community and write_community and read_community == write_community:
            raise ValueError("read_community and write_community must differ")

        payload: dict = {
            "SnmpV1Enable":  v1_enable,
            "SnmpV2CEnable": v2_enable,
            "SnmpV3Enable":  v3_enable,
            "Oem": {"Public": {"EncryptFlag": False}},
        }
        if read_community is not None:
            payload["ReadOnlyCommunity"] = read_community
        if write_community is not None:
            payload["ReadWriteCommunity"] = write_community

        _, etag = self._c.get_with_etag(_SNMP)
        return self._c.patch(_SNMP, payload, etag=etag)

    def add_trap_server(
        self,
        index: int,
        destination: str,
        port: int = 162,
        *,
        version: str = "V2C",
        community: Optional[str] = None,
    ) -> dict:
        """
        Enable a trap server slot (index 0-3).
        Reads current config, updates only the given slot, patches back.
        """
        if index not in range(4):
            raise ValueError("Trap server index must be 0-3")

        body, etag = self._c.get_with_etag(_SNMP)
        trap = body.get("SnmpTrapNotification", {})
        servers = trap.get("TrapServer") or [
            {"Id": i, "Destination": "0.0.0.0", "Port": 162, "Enabled": False}
            for i in range(4)
        ]
        for s in servers:
            if s.get("Id") == index:
                s.update({"Destination": destination, "Port": port, "Enabled": True})
                break

        patch: dict = {
            "SnmpTrapNotification": {
                "TrapServer": servers,
                "TrapVersion": version,
            }
        }
        if community:
            patch["SnmpTrapNotification"]["Community"] = community

        return self._c.patch(_SNMP, patch, etag=etag)

    def remove_trap_server(self, index: int) -> dict:
        """Disable a trap server slot."""
        if index not in range(4):
            raise ValueError("Trap server index must be 0-3")
        body, etag = self._c.get_with_etag(_SNMP)
        trap = body.get("SnmpTrapNotification", {})
        servers = trap.get("TrapServer", [])
        for s in servers:
            if s.get("Id") == index:
                s.update({"Enabled": False, "Destination": "0.0.0.0"})
                break
        return self._c.patch(_SNMP, {"SnmpTrapNotification": {"TrapServer": servers}}, etag=etag)

    def test_trap(self) -> dict:
        """Send a test SNMP trap event."""
        return self._c.post(f"{_SNMP}/Actions/SnmpService.SubmitTestEvent")
