"""User account management."""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..client import KaytusClient

_ACCOUNTS = "/redfish/v1/AccountService/Accounts"
_ACCT_SVC = "/redfish/v1/AccountService"

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

    # ── Account policy ────────────────────────────────────

    def policy(self) -> dict:
        """Return account lockout and password policy."""
        d = self._c.get(_ACCT_SVC)
        return {
            "lockout_threshold":    d.get("AccountLockoutThreshold"),
            "lockout_duration_min": d.get("AccountLockoutDuration"),
            "min_password_length":  d.get("MinPasswordLength"),
            "max_password_length":  d.get("MaxPasswordLength"),
            "service_enabled":      d.get("ServiceEnabled"),
        }

    def set_lockout_policy(
        self,
        *,
        threshold: Optional[int] = None,
        duration_min: Optional[int] = None,
    ) -> dict:
        """
        Set account lockout policy.
        threshold   : failed attempts before lockout (0 = disable lockout)
        duration_min: lockout duration in minutes
        """
        payload: dict = {}
        if threshold is not None:
            payload["AccountLockoutThreshold"] = threshold
        if duration_min is not None:
            payload["AccountLockoutDuration"] = duration_min
        return self._c.patch(_ACCT_SVC, payload)

    def set_password_policy(
        self,
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
    ) -> dict:
        """Set minimum and/or maximum password length."""
        payload: dict = {}
        if min_length is not None:
            payload["MinPasswordLength"] = min_length
        if max_length is not None:
            payload["MaxPasswordLength"] = max_length
        return self._c.patch(_ACCT_SVC, payload)

    # ── LDAP ─────────────────────────────────────────────

    def ldap_summary(self) -> dict:
        """Return current LDAP configuration summary."""
        d = self._c.get(_ACCT_SVC)
        ldap = d.get("LDAP", {})
        search = ldap.get("LDAPService", {}).get("SearchSettings", {})
        auth = ldap.get("Authentication", {})
        return {
            "enabled":       d.get("LDAP", {}).get("ServiceEnabled"),
            "server":        auth.get("Username"),
            "base_dn":       (search.get("BaseDistinguishedNames") or [""])[0],
            "username_attr": search.get("UsernameAttribute"),
            "groups_attr":   search.get("GroupsAttribute"),
        }

    def configure_ldap(
        self,
        server_address: str,
        base_dn: str,
        bind_dn: str = "",
        bind_password: str = "",
        *,
        username_attribute: str = "uid",
        groups_attribute: str = "gidNumber",
        enabled: bool = True,
    ) -> dict:
        """Configure LDAP authentication settings."""
        return self._c.patch(_ACCT_SVC, {
            "LDAP": {
                "ServiceEnabled": enabled,
                "Authentication": {
                    "AuthenticationType": "UsernameAndPassword",
                    "Username": bind_dn,
                    "Password": bind_password,
                },
                "LDAPService": {
                    "SearchSettings": {
                        "BaseDistinguishedNames": [base_dn],
                        "UsernameAttribute": username_attribute,
                        "GroupsAttribute": groups_attribute,
                    }
                },
            }
        })
