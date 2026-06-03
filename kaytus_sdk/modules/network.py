"""Network: BMC ethernet (eth0), hostname, DNS, static IP, NTP, protocols."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import KaytusClient

_ETH0  = "/redfish/v1/Managers/1/EthernetInterfaces/eth0"
_NTP   = "/redfish/v1/Managers/1/NtpService"
_PROTO = "/redfish/v1/Managers/1/NetworkProtocol"


class NetworkModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    # ── Ethernet / IP ─────────────────────────────────────

    def ethernet_info(self) -> dict:
        """Full eth0 interface resource."""
        return self._c.get(_ETH0)

    def summary(self) -> dict:
        """Concise network summary."""
        d = self.ethernet_info()
        ipv4 = (d.get("IPv4Addresses") or [{}])[0]
        return {
            "hostname":    d.get("HostName"),
            "mac":         d.get("MACAddress"),
            "ip":          ipv4.get("Address"),
            "subnet":      ipv4.get("SubnetMask"),
            "gateway":     ipv4.get("Gateway"),
            "dhcp":        d.get("DHCPv4", {}).get("DHCPEnabled"),
            "dns_servers": d.get("NameServers", []),
            "ipv6":        [a.get("Address") for a in d.get("IPv6Addresses", [])],
        }

    def set_hostname(self, hostname: str) -> dict:
        """Set BMC hostname and disable auto-hostname config."""
        return self._c.patch_with_etag(_ETH0, {
            "HostName": hostname,
            "Oem": {"Public": {"DNS": {"HostNameAutoConfigedEnable": False}}},
        })

    def set_dns(self, servers: list[str]) -> dict:
        """Set DNS nameservers (up to 3). Refreshes ETag before patching."""
        return self._c.patch_with_etag(_ETH0, {
            "NameServers": servers,
            "Oem": {"Public": {"DNS": {
                "RegistionOption": "Hostname",
                "DomainManual": False,
                "Manual": True,
            }}},
        })

    def set_hostname_and_dns(self, hostname: str, dns_servers: list[str]) -> None:
        """Set hostname then DNS (two sequential ETag-aware PATCHes)."""
        self.set_hostname(hostname)
        self.set_dns(dns_servers)

    def set_static_ip(self, ip: str, subnet: str, gateway: str) -> dict:
        """Configure static IPv4 address."""
        return self._c.patch_with_etag(_ETH0, {
            "DHCPv4": {"DHCPEnabled": False},
            "IPv4StaticAddresses": [{"Address": ip, "SubnetMask": subnet, "Gateway": gateway}],
        })

    def enable_dhcp(self) -> dict:
        """Switch BMC management interface to DHCP."""
        return self._c.patch_with_etag(_ETH0, {"DHCPv4": {"DHCPEnabled": True}})

    # ── NTP ──────────────────────────────────────────────

    def ntp_info(self) -> dict:
        """Full NTP service resource."""
        return self._c.get(_NTP)

    def ntp_summary(self) -> dict:
        """Concise NTP status."""
        d = self.ntp_info()
        return {
            "enabled":   d.get("ServiceEnabled"),
            "type":      d.get("NtpServerType"),
            "primary":   d.get("PrimaryNtpServer"),
            "secondary": d.get("SecondaryNtpServer"),
            "interval":  d.get("PollingInterval"),
        }

    def set_ntp(
        self,
        primary: str,
        secondary: str = "",
        *,
        enabled: bool = True,
        interval: int = 60,
    ) -> dict:
        return self._c.patch(_NTP, {
            "ServiceEnabled":    enabled,
            "NtpServerType":     "Static",
            "PrimaryNtpServer":  primary,
            "SecondaryNtpServer": secondary,
            "PollingInterval":   interval,
        })

    # ── Protocol settings ─────────────────────────────────

    def protocol_info(self) -> dict:
        """Full NetworkProtocol resource (HTTPS, IPMI, KVM ports etc.)."""
        return self._c.get(_PROTO)

    def set_https_timeout(self, seconds: int) -> dict:
        return self._c.patch(_PROTO, {"Oem": {"Public": {"HTTPS": {"Timeout": seconds}}}})

    def set_ipmi_enabled(self, enabled: bool) -> dict:
        return self._c.patch(_PROTO, {"IPMI": {"ProtocolEnabled": enabled}})

    def set_ssh_enabled(self, enabled: bool) -> dict:
        return self._c.patch(_PROTO, {"SSH": {"ProtocolEnabled": enabled}})

    def set_kvm_enabled(self, enabled: bool) -> dict:
        return self._c.patch(_PROTO, {"KVMIP": {"ProtocolEnabled": enabled}})

    # ── NTP extended ─────────────────────────────────────

    def set_ntp_servers(
        self,
        servers: list[str],
        *,
        enabled: bool = True,
        interval: int = 60,
    ) -> dict:
        """
        Configure up to 6 NTP servers.
        servers: list of NTP server addresses (index 0=primary, 1=secondary, …)
        """
        s = (servers + [""] * 6)[:6]
        return self._c.patch(_NTP, {
            "ServiceEnabled":      enabled,
            "NtpServerType":       "Static",
            "PrimaryNtpServer":    s[0],
            "SecondaryNtpServer":  s[1],
            "ThirdNtpServer":      s[2],
            "FourthNtpServer":     s[3],
            "FifthNtpServer":      s[4],
            "SixthNtpServer":      s[5],
            "PollingInterval":     interval,
        })

    # ── LLDP ─────────────────────────────────────────────

    _LLDP = "/redfish/v1/Managers/1/LldpService"

    def lldp_info(self) -> dict:
        """Return LLDP service status."""
        return self._c.get(self._LLDP)

    def set_lldp_enabled(self, enabled: bool) -> dict:
        """Enable or disable LLDP neighbour discovery."""
        return self._c.patch(self._LLDP, {"LldpEnabled": enabled})
