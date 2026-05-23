"""
Kaytus BMC Python SDK
=====================
Tested on : KR2280-X3 | BMC 4.35.00 | Redfish 1.18.0

Quick start — single server:
    from kaytus_sdk import KaytusClient

    with KaytusClient("10.255.40.100", "admin", "Pwd@10000") as bmc:
        print(bmc.system.overview())
        print(bmc.system.fan_summary())
        print(bmc.snmp.summary())
        bmc.syslog.set_server(0, "10.10.18.80", 514)

Bulk operations:
    from kaytus_sdk import bulk_run, ip_range, bulk_summary

    results = bulk_run(
        hosts     = ip_range("10.255.40", 100, 130),
        username  = "admin",
        password  = "Pwd@10000",
        operation = lambda c: c.system.overview(),
    )
    print(bulk_summary(results))

Modules:
    bmc.system   — overview, power, boot, thermal, fans, PSU
    bmc.network  — hostname, DNS, static IP, DHCP, NTP, protocols
    bmc.snmp     — V1/V2C/V3 config, trap servers
    bmc.syslog   — syslog server slots
    bmc.logs     — SEL, IDL, AuditLog, Alarms
    bmc.accounts — user CRUD
    bmc.bios     — attributes, reset, password, export
    bmc.firmware — inventory, BMC/BIOS version, TFTP update
    bmc.hardware — CPU, memory DIMMs, NIC adapters, PCIe, boards/FRU
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

__version__ = "2.0.1"
