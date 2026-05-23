# kaytus-bmc-sdk

A Python SDK for managing Kaytus BMC servers via the Redfish API.


## Tested Environment

| Component | Version |
|-----------|---------|
| Hardware  | Kaytus KR2280-X3 |
| BMC Firmware | 4.35.00 (2026-02-12) |
| BIOS | 04.03.00 (2026-01-29) |
| Redfish | 1.18.0 |
| Python | 3.10+ |

---

## Installation

```bash
pip install kaytus-bmc-sdk
```

**Requirements:** `requests >= 2.28`

---

## Quick Start

```python
from kaytus_sdk import KaytusClient

with KaytusClient("192.168.40.100", "admin", "password") as bmc:
    print(bmc.system.overview())
    print(bmc.system.fan_summary())
    print(bmc.network.summary())
```

---

## Bulk Operations

Run any operation across a range of servers concurrently:

```python
from kaytus_sdk import bulk_run, ip_range, bulk_summary

results = bulk_run(
    hosts     = ip_range("10.255.40", 100, 130),
    username  = "admin",
    password  = "password",
    operation = lambda c: c.system.overview(),
)
print(bulk_summary(results))
```

---

## Modules

### `bmc.system`

```python
bmc.system.overview()               # Single-request health/status summary
bmc.system.power_state()            # "On" | "Off" | "PoweringOn" | "PoweringOff"
bmc.system.power_on()
bmc.system.power_off()
bmc.system.shutdown()               # GracefulShutdown
bmc.system.reboot()                 # GracefulRestart
bmc.system.force_reboot()
bmc.system.power_cycle()
bmc.system.power_summary()          # Watts, PSU details, efficiency
bmc.system.fan_summary()            # RPM and ratio% for all fans
bmc.system.fan_control_info()       # FanControlMode, SmartCooling config
bmc.system.temperature_summary()    # All temperature sensors with thresholds
bmc.system.set_fan_mode("Auto")     # "Auto" | "Manual"
bmc.system.set_fan_speed(40)        # Manual mode: 0-100%
bmc.system.set_cooling_mode("LowNoise")   # "LowNoise" | "HighPerformance" | "Custom"
bmc.system.set_cpu_temp_target(85)  # SmartCooling CPU target temperature (°C)
bmc.system.set_boot_source("Pxe", enabled="Once")
bmc.system.set_indicator_led("Lit") # "Lit" | "Off" | "Blinking"
```

### `bmc.network`

```python
bmc.network.summary()
bmc.network.set_hostname("server-01")
bmc.network.set_dns(["1.1.1.1", "8.8.8.8"])
bmc.network.set_hostname_and_dns("server-01", ["1.1.1.1", "8.8.8.8"])
bmc.network.set_static_ip("10.0.0.100", "255.255.255.0", "10.0.0.1")
bmc.network.enable_dhcp()
bmc.network.ntp_summary()
bmc.network.set_ntp("ntp1.example.com", "ntp2.example.com")
bmc.network.set_https_timeout(1800)
bmc.network.set_ipmi_enabled(True)
```

### `bmc.snmp`

```python
bmc.snmp.summary()
bmc.snmp.configure(
    v1_enable=False, v2_enable=True, v3_enable=False,
    read_community="public", write_community="private"
)
bmc.snmp.add_trap_server(0, "10.0.0.50", 162, version="V2C")
bmc.snmp.remove_trap_server(0)
bmc.snmp.test_trap()
```

### `bmc.syslog`

```python
bmc.syslog.summary()
bmc.syslog.set_server(0, "10.0.0.50", 514,
    protocol="UDP",         # "UDP" | "TCP" | "TLS"
    log_type="Audit+IDL",   # "SEL" | "IDL" | "Audit" | combinations
    severity="Warning"      # "Critical" | "Warning" | "Info"
)
bmc.syslog.disable_server(0)
bmc.syslog.test()
```

### `bmc.logs`

```python
bmc.logs.sel(limit=50)          # System Event Log
bmc.logs.idl()                   # Intelligent Diagnose Log
bmc.logs.audit()                 # Audit log (config changes, logins)
bmc.logs.alarms()                # Active alarms
bmc.logs.all_logs()              # All services at once
bmc.logs.sel_summary()           # Count by severity
bmc.logs.recent_sel(10)
bmc.logs.recent_audit(20)
bmc.logs.search_idl("PSU")
bmc.logs.clear("SEL")           # "SEL" | "IDL" | "AuditLog"
```

### `bmc.accounts`

```python
bmc.accounts.summary()
bmc.accounts.create("ops", "SecurePass1!", role="Operator")
bmc.accounts.set_password("3", "NewPass!")
bmc.accounts.set_role("3", "ReadOnly")
bmc.accounts.set_enabled("3", False)
bmc.accounts.delete("3")
```

### `bmc.hardware`

```python
bmc.hardware.cpu_summary()      # Model, cores, threads, live MHz, TDP, cache, microcode
bmc.hardware.memory_summary()   # Populated DIMMs: capacity, type, speed, manufacturer
bmc.hardware.memory_total_gib()
bmc.hardware.nic_adapters()     # Network adapter cards
bmc.hardware.nic_ports("outboardPCIeCard25")
bmc.hardware.pcie_devices()     # All PCIe devices
bmc.hardware.boards()           # Chassis boards / FRU data
```

### `bmc.virtualmedia`

> Requires: `pip install 'kaytus-bmc-sdk[virtualmedia]'`  (or `pip install websockets>=14`)

```python
# One-shot: set boot source, reboot, and stream ISO until boot completes
bmc.virtualmedia.boot_cd("/path/to/proxmox-ve_9.2-1.iso")

# Step-by-step:
bmc.virtualmedia.set_boot_cd()              # set boot override → CD (Once, UEFI)
bmc.system.force_reboot()
bmc.virtualmedia.stream("/path/to/file.iso") # blocks until BMC disconnects

# Options:
bmc.virtualmedia.set_boot_cd(enabled="Continuous", mode="Legacy")
bmc.virtualmedia.boot_cd("/path/to/file.iso", boot_mode="Legacy", graceful=True)
```

### `bmc.bios`

```python
bmc.bios.version()
bmc.bios.info()
bmc.bios.set_attributes({"AttributeName": "Value"})
bmc.bios.reset_to_defaults()
bmc.bios.switch_active_bios("Bios-0")   # Dual BIOS slot switch
bmc.bios.export_config()
```

### `bmc.firmware`

```python
bmc.firmware.summary()          # All components: FanCPLD, PSU, VR, BIOS, BMC, CPLD
bmc.firmware.bmc_version()
bmc.firmware.bios_version()
bmc.firmware.tftp_update("tftp://10.0.0.1/bmc.bin")
bmc.firmware.update_status("task-id")
```

---

## Error Handling

```python
from kaytus_sdk import (
    KaytusAuthError,
    KaytusConnectionError,
    KaytusHTTPError,
    KaytusETagError,
    KaytusNotFoundError,
)

try:
    with KaytusClient("192.168.40.100", "admin", "password") as bmc:
        bmc.system.overview()
except KaytusConnectionError:
    print("Host unreachable or timed out")
except KaytusAuthError:
    print("Invalid credentials")
except KaytusHTTPError as e:
    print(f"HTTP error: {e.status_code}")
```

---

## Notes

- All PATCH operations are ETag-aware. The client handles ETag retrieval and stale-ETag retries automatically.
- Some BMC firmware versions return HTTP 400 for successful PATCH/POST operations. The SDK detects and handles this known firmware behaviour.
- SSL certificate verification is disabled by default (`verify_ssl=False`). Pass `verify_ssl=True` to enforce it.

---

## License

MIT

---

## Acknowledgements

<img src="https://raw.githubusercontent.com/erelbi/kaytus-bmc-sdk/main/docs/muhammed_musa_gungor.jpg" width="100" style="border-radius:50%" />

Special thanks to **Muhammed Musa Güngör** — our Infrastructure Hero —
for providing hardware access, testing support, and keeping the servers running
throughout the development and validation of this SDK.

<img src="https://raw.githubusercontent.com/erelbi/kaytus-bmc-sdk/main/docs/serdar_sarikaya.jpg" width="100" style="border-radius:50%" />

Special thanks to **Serdar Sarıkaya** for valuable support and contributions
during the development and testing of this SDK.

---

## Contributing

Pull requests are welcome. Please test changes against a real Kaytus BMC before submitting.
