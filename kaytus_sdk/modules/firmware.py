"""Firmware inventory and BMC/BIOS version helpers."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import KaytusClient

_FW_INVENTORY = "/redfish/v1/UpdateService/FirmwareInventory"
_UPDATE_SVC   = "/redfish/v1/UpdateService"


class FirmwareModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    def inventory(self) -> list[dict]:
        """Return full firmware component list (all members resolved)."""
        col = self._c.get(_FW_INVENTORY)
        result = []
        for m in col.get("Members", []):
            try:
                result.append(self._c.get(m["@odata.id"]))
            except Exception:
                pass
        return result

    def summary(self) -> list[dict]:
        """Return concise firmware inventory."""
        return [
            {
                "id":       fw.get("Id"),
                "name":     fw.get("Name"),
                "version":  fw.get("Version"),
                "status":   fw.get("Status", {}).get("Health"),
                "updateable": fw.get("Updateable"),
            }
            for fw in self.inventory()
        ]

    def bmc_version(self) -> str:
        """Return active BMC firmware version string."""
        try:
            return self._c.get(f"{_FW_INVENTORY}/ActiveBMC").get("Version", "")
        except Exception:
            return self._c.get("/redfish/v1/Managers/1").get("FirmwareVersion", "")

    def bios_version(self) -> str:
        """Return BIOS firmware version string."""
        return self._c.get("/redfish/v1/Systems/1").get("BiosVersion", "")

    def tftp_update(self, image_uri: str, targets: list[str] | None = None) -> dict:
        """
        Initiate firmware update via TFTP.
        image_uri : tftp://server/path/to/image.bin
        targets   : list of FirmwareInventory URIs (optional)
        """
        payload: dict = {"ImageURI": image_uri, "TransferProtocol": "TFTP"}
        if targets:
            payload["Targets"] = targets
        return self._c.post(
            f"{_UPDATE_SVC}/Actions/UpdateService.SimpleUpdate", payload
        )

    def update_status(self, task_id: str) -> dict:
        """Poll firmware update task status."""
        return self._c.get(f"/redfish/v1/TaskService/Tasks/{task_id}")
