"""SMTP email alert configuration.

Endpoint: /redfish/v1/Managers/1/SmtpService
Supports 4 recipient slots (Id 0-3).
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..client import KaytusClient

_SMTP = "/redfish/v1/Managers/1/SmtpService"

EVENT_LEVELS = ["Info", "Warning", "Critical"]


class SmtpModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    def info(self) -> dict:
        """Full SmtpService resource."""
        return self._c.get(_SMTP)

    def summary(self) -> dict:
        """Concise SMTP status."""
        d = self.info()
        cfg = d.get("SmtpCfg", {})
        return {
            "enabled":      cfg.get("SmtpEnable"),
            "server":       cfg.get("ServerAddr"),
            "port":         cfg.get("SmtpPort"),
            "secure_port":  cfg.get("SmtpSecurePort"),
            "ssl_tls":      cfg.get("EnableSSLTLS"),
            "starttls":     cfg.get("EnableSTARTTLS"),
            "auth":         cfg.get("SMTPAUTH"),
            "sender":       cfg.get("SenderAddr"),
            "event_level":  cfg.get("EventLevel"),
            "recipients": [
                r for r in d.get("SmtpDestCfg", []) if r.get("Enabled")
            ],
        }

    def configure(
        self,
        server: str,
        *,
        port: int = 25,
        secure_port: int = 465,
        sender: str = "",
        username: str = "",
        password: str = "",
        auth: bool = False,
        ssl_tls: bool = False,
        starttls: bool = False,
        event_level: str = "Warning",
        enabled: bool = True,
        subject: str = "",
        include_hostname: bool = True,
        include_serial: bool = False,
        include_asset_tag: bool = False,
    ) -> dict:
        """Configure SMTP server settings."""
        if event_level not in EVENT_LEVELS:
            raise ValueError(f"event_level must be one of {EVENT_LEVELS}")
        return self._c.patch(_SMTP, {
            "SmtpCfg": {
                "SmtpEnable":     enabled,
                "ServerAddr":     server,
                "SmtpPort":       port,
                "SmtpSecurePort": secure_port,
                "SenderAddr":     sender,
                "UserName":       username,
                "PassWord":       password,
                "SMTPAUTH":       auth,
                "EnableSSLTLS":   ssl_tls,
                "EnableSTARTTLS": starttls,
                "EventLevel":     event_level,
                "Subject":        subject,
                "HostName":       include_hostname,
                "SerialNumber":   include_serial,
                "AssetTag":       include_asset_tag,
            }
        })

    def add_recipient(
        self,
        index: int,
        email: str,
        description: str = "",
    ) -> dict:
        """Enable a recipient slot (index 0-3)."""
        if index not in range(4):
            raise ValueError("Recipient index must be 0-3")
        d = self.info()
        dest = d.get("SmtpDestCfg", [
            {"Id": i, "EmailAddress": "", "Enabled": False, "Description": ""}
            for i in range(4)
        ])
        for r in dest:
            if r.get("Id") == index:
                r.update({"EmailAddress": email, "Enabled": True, "Description": description})
                break
        return self._c.patch(_SMTP, {"SmtpDestCfg": dest})

    def remove_recipient(self, index: int) -> dict:
        """Disable a recipient slot."""
        if index not in range(4):
            raise ValueError("Recipient index must be 0-3")
        d = self.info()
        dest = d.get("SmtpDestCfg", [])
        for r in dest:
            if r.get("Id") == index:
                r["Enabled"] = False
                break
        return self._c.patch(_SMTP, {"SmtpDestCfg": dest})

    def test(self, recipient_index: int = 0) -> dict:
        """Send a test email to the specified recipient slot."""
        if recipient_index not in range(4):
            raise ValueError("Recipient index must be 0-3")
        return self._c.post(
            f"{_SMTP}/SmtpService.SubmitTestEvent",
            {"Id": recipient_index},
        )

    def disable(self) -> dict:
        """Disable SMTP alerts."""
        return self._c.patch(_SMTP, {"SmtpCfg": {"SmtpEnable": False}})
