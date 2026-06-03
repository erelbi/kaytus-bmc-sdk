"""
Kaytus BMC Python SDK
=====================
Tested on : KR2280-X3 | BMC 4.35.00 | Redfish 1.18.0

Quick start — single server:
    from kaytus_sdk import KaytusClient

    with KaytusClient("192.168.40.100", "admin", "password") as bmc:
        print(bmc.system.overview())
        print(bmc.system.fan_summary())
        print(bmc.snmp.summary())
        bmc.syslog.set_server(0, "10.10.18.80", 514)

Bulk operations:
    from kaytus_sdk import bulk_run, ip_range, bulk_summary

    results = bulk_run(
        hosts     = ip_range("192.168.40", 100, 130),
        username  = "admin",
        password  = "password",
        operation = lambda c: c.system.overview(),
    )
    print(bulk_summary(results))

Modules:
    bmc.system        — overview, power, boot, thermal, fans, PSU, BMC reset, POST codes
    bmc.network       — hostname, DNS, static IP, DHCP, NTP (6 servers), LLDP, protocols
    bmc.snmp          — V1/V2C/V3 config, trap servers
    bmc.syslog        — syslog server slots
    bmc.logs          — SEL, IDL, AuditLog, Alarms
    bmc.accounts      — user CRUD, lockout policy, password policy, LDAP
    bmc.bios          — attributes, reset, password, export
    bmc.firmware      — inventory, BMC/BIOS version, TFTP/HTTP push update
    bmc.hardware      — CPU, memory DIMMs, NIC adapters, PCIe, boards/FRU
    bmc.drives        — disk/SSD inventory (temperature, SMART, capacity)
    bmc.smtp          — email alert configuration (4 recipient slots)
    bmc.events        — Redfish EventService subscriptions
    bmc.virtualmedia  — ISO boot via VMM WebSocket (requires websockets>=14)
"""
from .client import KaytusClient
from .exceptions import (
    KaytusError,
    KaytusAuthError,
    KaytusConnectionError,
    KaytusHTTPError,
    KaytusETagError,
    KaytusNotFoundError,
)
from .modules.bulk import bulk_run, ip_range, bulk_summary

__all__ = [
    "KaytusClient",
    "KaytusError",
    "KaytusAuthError",
    "KaytusConnectionError",
    "KaytusHTTPError",
    "KaytusETagError",
    "KaytusNotFoundError",
    "bulk_run",
    "ip_range",
    "bulk_summary",
]

__version__ = "2.2.0"
