"""User account management."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import KaytusClient

_ACCOUNTS = "/redfish/v1/AccountService/Accounts"

# Available roles on KR2280-X3
ROLES = ["Administrator", "Operator", "User", "No Group",
         "OEM1", "OEM2", "OEM3", "OEM4"]


class AccountsModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    def list(self) -> list[dict]:
        """Return all BMC user accounts (including disabled/empty slots)."""
        col = self._c.get(_ACCOUNTS)
        result = []
        for m in col.get("Members", []):
            try:
                result.append(self._c.get(m["@odata.id"]))
            except Exception:
                pass
        return result

    def summary(self) -> list[dict]:
        """Return only populated accounts (non-empty UserName)."""
        return [
            {
                "id":       a.get("Id"),
                "username": a.get("UserName"),
                "role":     a.get("RoleId"),
                "enabled":  a.get("Enabled"),
            }
            for a in self.list()
            if a.get("UserName")
        ]

    def get(self, account_id: str) -> dict:
        return self._c.get(f"{_ACCOUNTS}/{account_id}")

    def create(
        self,
        username: str,
        password: str,
        role: str = "Operator",
        *,
        enabled: bool = True,
    ) -> dict:
        return self._c.post(_ACCOUNTS, {
            "UserName": username,
            "Password": password,
            "RoleId":   role,
            "Enabled":  enabled,
        })

    def delete(self, account_id: str) -> dict:
        return self._c.delete(f"{_ACCOUNTS}/{account_id}")

    def set_password(self, account_id: str, new_password: str) -> dict:
        return self._c.patch(f"{_ACCOUNTS}/{account_id}", {"Password": new_password})

    def set_role(self, account_id: str, role: str) -> dict:
        return self._c.patch(f"{_ACCOUNTS}/{account_id}", {"RoleId": role})

    def set_enabled(self, account_id: str, enabled: bool) -> dict:
        return self._c.patch(f"{_ACCOUNTS}/{account_id}", {"Enabled": enabled})
