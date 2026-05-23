"""BIOS management: read, set attributes, reset, password, export/import."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import KaytusClient

_BIOS         = "/redfish/v1/Systems/1/Bios"
_BIOS_PENDING = "/redfish/v1/Systems/1/Bios/Settings"


class BiosModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    def info(self) -> dict:
        """Full BIOS resource with current attributes."""
        return self._c.get(_BIOS)

    def version(self) -> str:
        """Return BIOS version string, e.g. '04.03.00'."""
        return self._c.get("/redfish/v1/Systems/1").get("BiosVersion", "")

    def pending_settings(self) -> dict:
        """Return pending (next-boot) BIOS settings."""
        return self._c.get(_BIOS_PENDING)

    def set_attributes(self, attributes: dict) -> dict:
        """
        Set BIOS attributes applied on next reboot.
        attributes: {AttributeName: value, ...}
        """
        return self._c.patch(_BIOS_PENDING, {"Attributes": attributes})

    def reset_to_defaults(self) -> dict:
        """Reset BIOS to factory defaults (applied on next reboot)."""
        return self._c.post(f"{_BIOS}/Actions/Bios.ResetBios/")

    def change_password(
        self,
        password_name: str,
        old_password: str,
        new_password: str,
    ) -> dict:
        """
        password_name: AdministratorPassword | UserPassword
        """
        return self._c.post(f"{_BIOS}/Actions/Bios.ChangePassword/", {
            "PasswordName": password_name,
            "OldPassword":  old_password,
            "NewPassword":  new_password,
        })

    def export_config(self) -> dict:
        """Export BIOS configuration."""
        return self._c.post("/redfish/v1/Systems/1/Actions/BIOS.ExportConfiguration")

    def switch_active_bios(self, slot: str) -> dict:
        """
        Switch between dual BIOS slots (KR2280 has BiosNum=2).
        slot: Bios-0 | Bios-1
        """
        if slot not in ("Bios-0", "Bios-1"):
            raise ValueError("slot must be 'Bios-0' or 'Bios-1'")
        return self._c.post("/redfish/v1/Systems/1/Actions/BIOS.SwitchActiveBios", {
            "ActiveBios": slot
        })
