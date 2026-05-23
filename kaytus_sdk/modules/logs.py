"""Log services: SEL, IDL, AuditLog, Alarms."""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..client import KaytusClient

_BASE = "/redfish/v1/Managers/1/LogServices"

# Confirmed on KR2280-X3: SEL (33 entries), IDL (40), AuditLog (100), Alarms (0)
_SERVICES = ["SEL", "IDL", "AuditLog", "Alarms"]


class LogsModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    def _entries(self, service: str, limit: Optional[int] = None) -> list[dict]:
        data = self._c.get(f"{_BASE}/{service}/Entries")
        members = data.get("Members", [])
        return members[:limit] if limit else members

    def sel(self, limit: Optional[int] = None) -> list[dict]:
        """System Event Log (hardware events)."""
        return self._entries("SEL", limit)

    def idl(self, limit: Optional[int] = None) -> list[dict]:
        """Intelligent Diagnose Log."""
        return self._entries("IDL", limit)

    def audit(self, limit: Optional[int] = None) -> list[dict]:
        """Audit log (user actions, config changes)."""
        return self._entries("AuditLog", limit)

    def alarms(self) -> list[dict]:
        """Active alarms (empty list = all clear)."""
        return self._entries("Alarms")

    def all_logs(self) -> dict[str, list[dict]]:
        """Return all log services at once. Missing services return []."""
        result: dict[str, list[dict]] = {}
        for svc in _SERVICES:
            try:
                result[svc] = self._entries(svc)
            except Exception:
                result[svc] = []
        return result

    def clear(self, service: str) -> dict:
        """
        Clear a log service.  service: SEL | IDL | AuditLog
        """
        if service not in _SERVICES:
            raise ValueError(f"Unknown service '{service}'. Choose: {_SERVICES}")
        return self._c.post(f"{_BASE}/{service}/Actions/LogService.ClearLog")

    def sel_summary(self) -> dict:
        """Count SEL entries by severity."""
        entries = self.sel()
        counts: dict[str, int] = {}
        for e in entries:
            sev = e.get("Severity", "Unknown")
            counts[sev] = counts.get(sev, 0) + 1
        return {"total": len(entries), "by_severity": counts}

    def recent_sel(self, n: int = 10) -> list[dict]:
        """Return the N most recent SEL entries (BMC returns newest-first)."""
        return self._entries("SEL", n)

    def recent_audit(self, n: int = 20) -> list[dict]:
        return self._entries("AuditLog", n)

    def search_idl(self, keyword: str) -> list[dict]:
        """Filter IDL entries whose Message contains keyword (case-insensitive)."""
        kw = keyword.lower()
        return [e for e in self.idl() if kw in e.get("Message", "").lower()]
