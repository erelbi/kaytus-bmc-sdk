"""Hardware inventory: CPU, memory, NIC adapters, PCIe devices, FRU."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import KaytusClient

_SYSTEM  = "/redfish/v1/Systems/1"
_CHASSIS = "/redfish/v1/Chassis/1"


class HardwareModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    # ── CPU ───────────────────────────────────────────────

    def processors(self) -> list[dict]:
        """Return full detail for each processor."""
        col = self._c.get(f"{_SYSTEM}/Processors")
        result = []
        for m in col.get("Members", []):
            try:
                result.append(self._c.get(m["@odata.id"]))
            except Exception:
                pass
        return result

    def cpu_summary(self) -> list[dict]:
        """Concise CPU list including live frequency and cache info."""
        result = []
        for p in self.processors():
            if p.get("Status", {}).get("State") != "Enabled":
                continue
            oem = p.get("Oem", {}).get("Public", {})
            result.append({
                "id":              p.get("Id"),
                "model":           p.get("Model"),
                "manufacturer":    p.get("Manufacturer"),
                "socket":          p.get("Socket"),
                "cores":           p.get("TotalCores"),
                "threads":         p.get("TotalThreads"),
                "max_mhz":         p.get("MaxSpeedMHz"),
                "current_mhz":     oem.get("CurrentSpeedMHz"),
                "turbo_on_mhz":    oem.get("TurboEnableMaxSpeedMHz"),
                "turbo_off_mhz":   oem.get("TurboDisableMaxSpeedMHz"),
                "max_tdp_watts":   p.get("MaxTDPWatts"),
                "l1_cache_kib":    oem.get("L1CacheKiB"),
                "l2_cache_kib":    oem.get("L2CacheKiB"),
                "l3_cache_kib":    oem.get("L3CacheKiB"),
                "serial":          p.get("SerialNumber"),
                "microcode":       p.get("ProcessorId", {}).get("MicrocodeInfo"),
                "status":          p.get("Status", {}).get("Health"),
            })
        return result

    # ── Memory ────────────────────────────────────────────

    def memory_dimms(self) -> list[dict]:
        """Return full detail for each DIMM slot."""
        col = self._c.get(f"{_SYSTEM}/Memory")
        result = []
        for m in col.get("Members", []):
            try:
                result.append(self._c.get(m["@odata.id"]))
            except Exception:
                pass
        return result

    def memory_summary(self) -> list[dict]:
        """Concise list of populated DIMMs."""
        return [
            {
                "id":        d.get("Id"),
                "capacity_gib": round((d.get("CapacityMiB") or 0) / 1024, 1),
                "type":      d.get("MemoryDeviceType"),
                "speed_mhz": d.get("OperatingSpeedMhz"),
                "manufacturer": d.get("Manufacturer"),
                "serial":    d.get("SerialNumber"),
                "part":      d.get("PartNumber"),
                "status":    d.get("Status", {}).get("Health"),
            }
            for d in self.memory_dimms()
            if d.get("Status", {}).get("State") == "Enabled"
        ]

    def memory_total_gib(self) -> float:
        """Return total installed memory in GiB."""
        return float(
            self._c.get(_SYSTEM)
            .get("MemorySummary", {})
            .get("TotalSystemMemoryGiB", 0)
        )

    # ── NIC adapters ──────────────────────────────────────

    def nic_adapters(self) -> list[dict]:
        """Return concise list of network adapters."""
        col = self._c.get(f"{_CHASSIS}/NetworkAdapters")
        result = []
        for m in col.get("Members", []):
            try:
                d = self._c.get(m["@odata.id"])
                result.append({
                    "id":           d.get("Id"),
                    "manufacturer": d.get("Manufacturer"),
                    "model":        d.get("Model"),
                    "part_number":  d.get("PartNumber"),
                    "serial":       d.get("SerialNumber"),
                    "status":       d.get("Status", {}).get("Health"),
                })
            except Exception:
                pass
        return result

    def nic_ports(self, adapter_id: str) -> list[dict]:
        """Return network ports for a given adapter ID."""
        col = self._c.get(
            f"{_CHASSIS}/NetworkAdapters/{adapter_id}/NetworkPorts"
        )
        result = []
        for m in col.get("Members", []):
            try:
                d = self._c.get(m["@odata.id"])
                result.append({
                    "id":         d.get("Id"),
                    "link_speed": d.get("CurrentLinkSpeedMbps"),
                    "link_status": d.get("LinkStatus"),
                    "mac":        d.get("AssociatedNetworkAddresses", []),
                    "status":     d.get("Status", {}).get("Health"),
                })
            except Exception:
                pass
        return result

    # ── PCIe ─────────────────────────────────────────────

    def pcie_devices(self) -> list[dict]:
        """Return concise list of PCIe devices."""
        col = self._c.get(f"{_CHASSIS}/PCIeDevices")
        result = []
        for m in col.get("Members", []):
            try:
                d = self._c.get(m["@odata.id"])
                result.append({
                    "id":           d.get("Id"),
                    "name":         d.get("Name"),
                    "manufacturer": d.get("Manufacturer"),
                    "device_type":  d.get("DeviceType"),
                    "status":       d.get("Status", {}).get("Health"),
                })
            except Exception:
                pass
        return result

    # ── FRU boards ───────────────────────────────────────

    def boards(self) -> list[dict]:
        """Return chassis board/FRU list."""
        col = self._c.get(f"{_CHASSIS}/Boards")
        result = []
        for m in col.get("Members", []):
            try:
                d = self._c.get(m["@odata.id"])
                result.append({
                    "id":           d.get("Id"),
                    "name":         d.get("Name"),
                    "manufacturer": d.get("Manufacturer"),
                    "part_number":  d.get("PartNumber"),
                    "serial":       d.get("SerialNumber"),
                    "version":      d.get("Version"),
                    "status":       d.get("Status", {}).get("Health"),
                })
            except Exception:
                pass
        return result
