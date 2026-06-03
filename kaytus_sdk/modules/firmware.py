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

    def http_push_update(self, local_path: str, targets: list[str] | None = None) -> dict:
        """
        Initiate firmware update by uploading a local image file via HTTP multipart.
        local_path: path to the firmware image file (.bin / .tar / .hpm)
        targets   : list of FirmwareInventory URIs (optional)
        """
        import os
        import requests as _requests

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Firmware image not found: {local_path}")

        push_uri = self._c.get(_UPDATE_SVC).get("HttpPushUri", "")
        if not push_uri:
            raise RuntimeError("BMC does not advertise an HttpPushUri")

        url = f"{self._c.base_url}{push_uri}"
        token = self._c._session.headers.get("X-Auth-Token", "")
        headers = {"X-Auth-Token": token}

        with open(local_path, "rb") as f:
            resp = _requests.post(
                url,
                headers=headers,
                files={"UpdateFile": (os.path.basename(local_path), f, "application/octet-stream")},
                verify=False,
                timeout=300,
            )
        return self._c._handle(resp, "POST", push_uri)

    def tasks(self) -> list[dict]:
        """Return all firmware-related tasks."""
        col = self._c.get("/redfish/v1/TaskService/Tasks")
        result = []
        for m in col.get("Members", []):
            try:
                result.append(self._c.get(m["@odata.id"]))
            except Exception:
                pass
        return result

    def update_status(self, task_id: str) -> dict:
        """Poll firmware update task status."""
        return self._c.get(f"/redfish/v1/TaskService/Tasks/{task_id}")
