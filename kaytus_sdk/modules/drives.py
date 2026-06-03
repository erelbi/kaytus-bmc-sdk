"""Drive/disk inventory.

On KR2280-X3 the standard Members list in Chassis/1/Drives is empty;
real members are in Oem.Public.Members.  Both paths are tried so the
module works on any firmware variant.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..client import KaytusClient

_DRIVES = "/redfish/v1/Chassis/1/Drives"


class DrivesModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    def _member_urls(self) -> list[str]:
        """Return drive URL list, falling back to Oem.Public.Members."""
        col = self._c.get(_DRIVES)
        members = col.get("Members", [])
        if not members:
            members = col.get("Oem", {}).get("Public", {}).get("Members", [])
        return [m["@odata.id"] for m in members if "@odata.id" in m]

    def list(self) -> list[dict]:
        """Return raw Redfish dict for every drive."""
        result = []
        for url in self._member_urls():
            try:
                result.append(self._c.get(url))
            except Exception:
                pass
        return result

    def summary(self) -> list[dict]:
        """Concise drive table (only present/enabled drives)."""
        return [
            {
                "id":            d.get("Id"),
                "name":          d.get("Name"),
                "location":      self._location(d),
                "backplane":     self._backplane(d),
                "manufacturer":  d.get("Manufacturer"),
                "model":         d.get("Model"),
                "serial":        (d.get("SerialNumber") or "").strip(),
                "firmware":      d.get("FirmwareVersion") or d.get("Revision"),
                "media_type":    d.get("MediaType"),
                "protocol":      d.get("Protocol"),
                "capacity_tb":   round(
                    (d.get("CapacityBytes") or 0) / 1e12, 2
                ),
                "speed_gbs":     d.get("NegotiatedSpeedGbs"),
                "temp_c":        d.get("Oem", {}).get("Public", {}).get("Temperature"),
                "life_left_pct": d.get("PredictedMediaLifeLeftPercent"),
                "smart_warn":    d.get("Oem", {}).get("Public", {}).get("SmartWarnings"),
                "health":        d.get("Status", {}).get("Health"),
                "state":         d.get("Status", {}).get("State"),
            }
            for d in self.list()
            if d.get("Status", {}).get("State") != "Absent"
        ]

    def health_summary(self) -> dict:
        """Count drives by health state."""
        counts: dict[str, int] = {}
        total = 0
        for d in self.summary():
            h = d.get("health") or "Unknown"
            counts[h] = counts.get(h, 0) + 1
            total += 1
        return {"total": total, "by_health": counts}

    def unhealthy(self) -> list[dict]:
        """Return drives that are not OK or have SMART warnings."""
        return [
            d for d in self.summary()
            if d.get("health") != "OK"
            or (d.get("smart_warn") not in (None, 255))
        ]

    def get(self, drive_id: str) -> dict:
        """Return full Redfish resource for one drive by ID."""
        return self._c.get(f"{_DRIVES}/{drive_id}")

    def set_indicator_led(self, drive_id: str, state: str = "Lit") -> dict:
        """state: Lit | Off | Blinking"""
        return self._c.patch(f"{_DRIVES}/{drive_id}", {"IndicatorLED": state})

    # ── Helpers ───────────────────────────────────────────

    @staticmethod
    def _location(d: dict) -> Optional[str]:
        locs = d.get("Location") or d.get("PhysicalLocation")
        if isinstance(locs, list) and locs:
            return locs[0].get("Info")
        if isinstance(locs, dict):
            return locs.get("Info")
        return None

    @staticmethod
    def _backplane(d: dict) -> Optional[str]:
        locs = d.get("Location") or []
        if isinstance(locs, list) and locs:
            return locs[0].get("Placement", {}).get("AdditionalInfo")
        return None
