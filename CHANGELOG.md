# Changelog

All notable changes to this project will be documented in this file.

## [2.2.0] - 2026-06-03

### Added
- `drives` module: disk/SSD inventory with SMART warnings, temperature, capacity, indicator LED control
- `smtp` module: email alert configuration — server settings, 4 recipient slots, test email
- `events` module: Redfish EventService subscriptions (create, delete, test event)
- `accounts.policy()`: read lockout + password policy
- `accounts.set_lockout_policy()`, `accounts.set_password_policy()`: account security settings
- `accounts.ldap_summary()`, `accounts.configure_ldap()`: LDAP authentication configuration
- `firmware.http_push_update()`: upload firmware image via HTTP multipart (HttpPushUri)
- `firmware.tasks()`: list all firmware-related tasks
- `network.set_ssh_enabled()`, `network.set_kvm_enabled()`: SSH and KVM protocol toggle
- `network.set_ntp_servers()`: configure up to 6 NTP servers with polling interval
- `network.lldp_info()`, `network.set_lldp_enabled()`: LLDP neighbour discovery
- `system.watchdog_info()`, `system.set_watchdog()`: host watchdog timer configuration
- `system.bmc_reset()`, `system.bmc_reset_to_defaults()`: BMC restart and factory reset
- `system.bmc_time()`: current BMC date/time string
- `system.post_codes()`: recent BIOS POST codes
- `system.collect_onekeylog()`, `system.onekeylog_status()`: one-key diagnostic log collection

### Fixed
- `syslog.set_server()` and `syslog.disable_server()` now send the full server list on PATCH
  instead of a single-element list (previously wiped other slots)

---

## [2.1.0] - 2026-05-23

### Added
- `virtualmedia` module: ISO boot via Kaytus VMM WebSocket protocol
- `virtualmedia.stream()`: serve a local ISO file to the BMC (blocking until BMC disconnects)
- `virtualmedia.set_boot_cd()`: Redfish PATCH to set BootSourceOverrideTarget=Cd
- `virtualmedia.boot_cd()`: one-shot helper — set boot source, reboot, stream ISO
- Requires `websockets>=14` (optional: `pip install 'kaytus-bmc-sdk[virtualmedia]'`)

### Notes
- VMM auth: binary `VMM_AUTH_PKT` is skipped when `X-Auth-Token` is in the WebSocket upgrade
  headers (NGINX pre-authenticates); `VMM_VMEDIA_INFO_PKT` sent directly after `VMM_CONNECT_PKT`

---

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
