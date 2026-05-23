"""System operations: overview, power control, boot, thermal, power."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import KaytusClient

_SYSTEM  = "/redfish/v1/Systems/1"
_CHASSIS = "/redfish/v1/Chassis/1"
_OEM     = "/redfish/v1/OemService/Overview"

POWER_ACTIONS = [
    "On", "ForceOff", "GracefulShutdown", "GracefulRestart",
    "ForceRestart", "Nmi", "ForceOn", "PushPowerButton", "PowerCycle",
]
BOOT_TARGETS = ["None", "Pxe", "Hdd", "Cd", "Diags", "BiosSetup", "Usb"]


class SystemModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    # ── Overview ──────────────────────────────────────────

    def overview(self) -> dict:
        """Quick summary from OemService/Overview (single request)."""
        d = self._c.get(_OEM)
        return {
            "hostname":     d.get("HostName"),
            "product":      d.get("ProductName"),
            "serial":       d.get("ProductSerial"),
            "bmc_version":  d.get("ActiveBMC"),
            "bios_version": d.get("BIOS"),
            "power_state":  d.get("PowerState"),
            "health":       d.get("HealthSumary", {}).get("Whole"),
            "health_detail": d.get("HealthSumary", {}),
            "inlet_temp_c": d.get("InletTemperature", {}).get("Reading"),
            "total_watts":  d.get("Power", {}).get("TotalPower"),
            "memory_gib":   d.get("TotalSystemMemoryGiB"),
            "mac":          d.get("MACAddress"),
            "ip":           d.get("ManagementIPv4"),
            "devices":      d.get("DevicePresentNumber", {}),
            "alarms": {
                "critical": d.get("AlarmCriticalNumber", 0),
                "warning":  d.get("AlarmWarningNumber", 0),
            },
        }

    def info(self) -> dict:
        """Full /redfish/v1/Systems/1 resource."""
        return self._c.get(_SYSTEM)

    def chassis_info(self) -> dict:
        """Full /redfish/v1/Chassis/1 resource."""
        return self._c.get(_CHASSIS)

    # ── Power control ─────────────────────────────────────

    def power_control(self, action: str) -> dict:
        """
        Send power/reset action.
        action: On | ForceOff | GracefulShutdown | GracefulRestart |
                ForceRestart | Nmi | ForceOn | PushPowerButton | PowerCycle
        """
        if action not in POWER_ACTIONS:
            raise ValueError(f"Invalid action '{action}'. Choose: {POWER_ACTIONS}")
        return self._c.post(
            f"{_CHASSIS}/Actions/Chassis.Reset",
            {"ResetType": action},
        )

    def power_on(self)       -> dict: return self.power_control("On")
    def power_off(self)      -> dict: return self.power_control("ForceOff")
    def shutdown(self)       -> dict: return self.power_control("GracefulShutdown")
    def reboot(self)         -> dict: return self.power_control("GracefulRestart")
    def force_reboot(self)   -> dict: return self.power_control("ForceRestart")
    def power_cycle(self)    -> dict: return self.power_control("PowerCycle")
    def power_button(self)   -> dict: return self.power_control("PushPowerButton")

    def power_state(self) -> str:
        """Return current power state string: On | Off | PoweringOn | PoweringOff."""
        return self._c.get(_SYSTEM).get("PowerState", "")

    # ── System settings ───────────────────────────────────

    def set_indicator_led(self, state: str = "Lit") -> dict:
        """state: Lit | Off | Blinking"""
        return self._c.patch(_SYSTEM, {"IndicatorLED": state})

    def set_asset_tag(self, tag: str) -> dict:
        return self._c.patch(_SYSTEM, {"AssetTag": tag})

    def set_power_restore_policy(self, policy: str) -> dict:
        """policy: AlwaysOn | AlwaysOff | LastState"""
        return self._c.patch(_SYSTEM, {"PowerRestorePolicy": policy})

    def set_boot_source(
        self,
        target: str,
        *,
        enabled: str = "Once",
        mode: str = "UEFI",
    ) -> dict:
        """
        target : one of BOOT_TARGETS
        enabled: Once | Continuous | Disabled
        mode   : UEFI | Legacy
        """
        if target not in BOOT_TARGETS:
            raise ValueError(f"Invalid target '{target}'. Choose: {BOOT_TARGETS}")
        return self._c.patch(_SYSTEM, {
            "Boot": {
                "BootSourceOverrideTarget":  target,
                "BootSourceOverrideEnabled": enabled,
                "BootSourceOverrideMode":    mode,
            }
        })

    # ── Thermal ───────────────────────────────────────────

    def thermal(self) -> dict:
        """Full Chassis Thermal resource (fans + temperatures)."""
        return self._c.get(f"{_CHASSIS}/Thermal")

    def fan_summary(self) -> list[dict]:
        """Return concise fan speed list."""
        data = self.thermal()
        return [
            {
                "name":   f.get("Name"),
                "rpm":    f.get("Reading"),
                "ratio%": f.get("Oem", {}).get("Public", {}).get("SpeedRatio"),
                "status": f.get("Status", {}).get("Health"),
            }
            for f in data.get("Fans", [])
        ]

    def temperature_summary(self) -> list[dict]:
        """Return concise temperature sensor list (only sensors with a reading)."""
        data = self.thermal()
        return [
            {
                "name":       t.get("Name"),
                "celsius":    t.get("ReadingCelsius"),
                "upper_crit": t.get("UpperThresholdCritical"),
                "status":     t.get("Status", {}).get("Health"),
            }
            for t in data.get("Temperatures", [])
            if t.get("ReadingCelsius") is not None
        ]

    def fan_control_info(self) -> dict:
        """
        Return current fan control mode and SmartCooling config.
        FanControlMode: Auto | Manual
        SmartCooling.CoolingMode: LowNoise | HighPerformance | Custom
        """
        oem = self.thermal().get("Oem", {}).get("Public", {})
        sc  = oem.get("SmartCooling", {})
        return {
            "fan_control_mode":  oem.get("FanControlMode"),
            "cooling_mode":      sc.get("CoolingMode"),
            "smart_cooling":     sc.get("SmartCooling"),
            "cpu_target_c":      sc.get("CPUTarget"),
            "cpu_margin_target": sc.get("CPUMarginTarget"),
            "cpu_tjmax":         sc.get("CPUTjmax"),
            "inlet_temp_duty":   sc.get("InletTempDuty", []),
        }

    def set_fan_mode(self, mode: str) -> dict:
        """
        Set fan control mode.
        mode: Auto | Manual
        In Manual mode, use set_fan_speed() to set the ratio.
        """
        if mode not in ("Auto", "Manual"):
            raise ValueError("mode must be 'Auto' or 'Manual'")
        return self._c.patch_with_etag(
            f"{_CHASSIS}/Thermal",
            {"Oem": {"Public": {"FanControlMode": mode}}},
        )

    def set_fan_speed(self, ratio: int) -> dict:
        """
        Set global fan speed ratio in Manual mode (0-100%).
        First call set_fan_mode('Manual'), then set ratio.
        """
        if not 0 <= ratio <= 100:
            raise ValueError("ratio must be 0-100")
        return self._c.patch_with_etag(
            f"{_CHASSIS}/Thermal",
            {"Oem": {"Public": {"FanControlMode": "Manual", "FanSpeedRatio": ratio}}},
        )

    def set_cooling_mode(self, mode: str) -> dict:
        """
        Set SmartCooling mode.
        mode: LowNoise | HighPerformance | Custom
        """
        if mode not in ("LowNoise", "HighPerformance", "Custom"):
            raise ValueError("mode must be LowNoise | HighPerformance | Custom")
        return self._c.patch_with_etag(
            f"{_CHASSIS}/Thermal",
            {"Oem": {"Public": {"SmartCooling": {"CoolingMode": mode}}}},
        )

    def set_cpu_temp_target(self, target_c: int) -> dict:
        """
        Set SmartCooling CPU temperature target (°C).
        Fan controller tries to keep CPU at or below this temperature.
        """
        return self._c.patch_with_etag(
            f"{_CHASSIS}/Thermal",
            {"Oem": {"Public": {"SmartCooling": {"CPUTarget": target_c}}}},
        )

    # ── Power ─────────────────────────────────────────────

    def power(self) -> dict:
        """Full Chassis Power resource."""
        return self._c.get(f"{_CHASSIS}/Power")

    def power_summary(self) -> dict:
        """Return concise power consumption + PSU details."""
        data = self.power()
        oem = data.get("Oem", {}).get("Public", {})
        psus = [
            {
                "name":          psu.get("Name"),
                "output_watts":  psu.get("LastPowerOutputWatts"),
                "input_voltage": psu.get("LineInputVoltage"),
                "efficiency%":   round((psu.get("EfficiencyPercent") or 0) * 100, 1),
                "status":        psu.get("Status", {}).get("Health"),
                "serial":        psu.get("SerialNumber"),
                "firmware":      psu.get("FirmwareVersion"),
            }
            for psu in data.get("PowerSupplies", [])
        ]
        return {
            "total_watts":   oem.get("TotalPower"),
            "cpu_watts":     oem.get("CurrentCPUPowerWatts"),
            "memory_watts":  oem.get("CurrentMemoryPowerWatts"),
            "fan_watts":     oem.get("CurrentFANPowerWatts"),
            "limit_status":  oem.get("PowerLimitStatus"),
            "redundancy":    oem.get("RedundantStatus"),
            "psus":          psus,
        }
