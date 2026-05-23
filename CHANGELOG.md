# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-05-23

### Added
- `hardware` module: CPU detail (live MHz, TDP, cache sizes, microcode), memory DIMMs,
  NIC adapters with port listing, PCIe device inventory, chassis boards/FRU
- `system.fan_control_info()`: exposes FanControlMode, SmartCooling config, InletTempDuty table
- `system.set_fan_mode()`: switch between Auto and Manual fan control
- `system.set_fan_speed()`: set global fan speed ratio in manual mode
- `system.set_cooling_mode()`: LowNoise / HighPerformance / Custom
- `system.set_cpu_temp_target()`: SmartCooling CPU temperature target
- `system.overview()` now sourced from OemService/Overview (single request, richer data)
- `network.ntp_summary()`, `network.set_ipmi_enabled()`
- `firmware.update_status()` for polling task progress
- `logs.search_idl()` keyword filter

### Changed
- `system.overview()` switched from Systems/1 to OemService/Overview for richer single-request data
- `hardware.cpu_summary()` extended with live frequency, turbo speeds, cache, TDP, microcode
- `system.power_control()` uses Chassis/1/Actions/Chassis.Reset (confirmed working path)
- `syslog.set_server()` strips read-only fields before PATCH (prevents 400 errors)
- Package version bumped to 2.0.0

### Tested on
- Kaytus KR2280-X3 | BMC 4.35.00 | BIOS 04.03.00 | Redfish 1.18.0

---

## [1.0.0] - 2026-05-01

### Added
- Initial release
- Core Redfish client with session management and ETag support
- Modules: system, network, snmp, syslog, logs, accounts, bios, firmware
- Bulk operation support via `bulk_run()` and `ip_range()`
- Automatic retry on stale ETag (HTTP 428)
- Kaytus firmware 400/success bug workaround
