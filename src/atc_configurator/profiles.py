"""Profile catalogue loading and conditional logical-signal expansion."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any


_REQUIREMENT_RANK = {
    "required": 0,
    "conditional": 1,
    "recommended": 2,
    "optional": 3,
    "internal": 4,
}


def load_profile_catalog(path: str | Path) -> dict[str, Any]:
    import json
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def find_profile(catalog: dict[str, Any], profile_id: str) -> dict[str, Any] | None:
    return next((item for item in catalog.get("profiles", []) if item.get("id") == profile_id), None)


def required_signal_specs(config: dict[str, Any], profile: dict[str, Any]) -> list[dict[str, str]]:
    """Build only the physical DI/DO signals required by this configuration.

    Encoder, Stepgen, Fieldbus and internal LinuxCNC HAL resources are checked
    separately; they must never be auto-mapped to ordinary digital I/O.
    """
    atc = config["atc"]
    signals: dict[str, dict[str, str]] = {}

    def add(signal_id: str, direction: str, requirement: str = "required") -> None:
        current = signals.get(signal_id)
        candidate = {"id": signal_id, "direction": direction, "requirement": requirement}
        if current is None or _REQUIREMENT_RANK[requirement] < _REQUIREMENT_RANK[current["requirement"]]:
            signals[signal_id] = candidate

    for item in profile.get("signals", []):
        add(item["id"], item["direction"], item.get("requirement", "required"))

    magazine = atc["magazine"]
    count = magazine["pocket_count"]
    feedback = magazine["position_feedback"]
    method = feedback["method"]

    if method in ("gray_code", "binary_code"):
        bits = max(1, math.ceil(math.log2(count)))
        for bit in range(bits):
            add(f"MAG_CODE_BIT_{bit}", "input")
        if feedback.get("has_valid_strobe"):
            add("MAG_CODE_VALID", "input", "conditional")
    elif method == "bcd":
        digits = max(1, len(str(count)))
        for bit in range(digits * 4):
            add(f"MAG_BCD_BIT_{bit}", "input")
        if feedback.get("has_valid_strobe"):
            add("MAG_CODE_VALID", "input", "conditional")
    elif method == "home_index":
        add("MAG_HOME", "input")
        add("MAG_INDEX", "input")
    elif method == "per_pocket":
        for pocket in range(1, count + 1):
            add(f"MAG_POCKET_{pocket:03d}", "input")
    elif method in ("incremental_encoder", "absolute_encoder", "open_loop_step_count"):
        add("MAG_HOME", "input")
    elif method == "drive_in_position":
        add("MAG_IN_POSITION", "input")

    if magazine["drive"]["interface"] == "digital_io":
        add("MAG_CW", "output")
        add("MAG_CCW", "output")

    mechanism = atc["transfer"]["mechanism"]
    if mechanism in ("direct_pickup", "pot_movement"):
        add("MAG_IN_POSITION", "input")
    elif mechanism == "single_arm":
        for signal_id in ("ARM_HOME", "ARM_AT_SPINDLE", "ARM_AT_MAGAZINE",
                          "GRIPPER_TOOL_PRESENT", "GRIPPER_CLOSED", "GRIPPER_OPEN"):
            add(signal_id, "input")
        for signal_id in ("ARM_ROTATE_CMD", "ARM_EXTEND_CMD", "ARM_RETRACT_CMD",
                          "GRIPPER_OPEN_CMD", "GRIPPER_CLOSE_CMD"):
            add(signal_id, "output")
        add("MAG_IN_POSITION", "input")
    elif mechanism == "double_arm_180":
        for signal_id in ("ARM_HOME", "ARM_AT_EXCHANGE", "ARM_180_POSITION",
                          "GRIPPER_A_TOOL_PRESENT", "GRIPPER_B_TOOL_PRESENT",
                          "GRIPPER_A_CLOSED", "GRIPPER_B_CLOSED"):
            add(signal_id, "input")
        for signal_id in ("ARM_ROTATE_CW", "ARM_ROTATE_CCW", "ARM_EXTEND_CMD",
                          "ARM_RETRACT_CMD", "GRIPPER_A_OPEN_CMD", "GRIPPER_A_CLOSE_CMD",
                          "GRIPPER_B_OPEN_CMD", "GRIPPER_B_CLOSE_CMD"):
            add(signal_id, "output")
        add("MAG_IN_POSITION", "input")

    presentation = atc["transfer"].get("presentation", {}).get("mode", "fixed")
    if presentation == "pot_lift":
        add("POT_AT_EXCHANGE", "input")
        add("POT_HOME", "input")
        add("POT_UP_CMD", "output")
        add("POT_DOWN_CMD", "output")
    elif presentation == "pot_swing":
        add("POT_AT_EXCHANGE", "input")
        add("POT_HOME", "input")
        add("POT_SWING_IN_CMD", "output")
        add("POT_SWING_OUT_CMD", "output")
    elif presentation == "pot_slide":
        add("POT_AT_EXCHANGE", "input")
        add("POT_HOME", "input")
        add("POT_SLIDE_IN_CMD", "output")
        add("POT_SLIDE_OUT_CMD", "output")
    elif presentation == "magazine_retract":
        add("MAGAZINE_EXTENDED", "input")
        add("MAGAZINE_RETRACTED", "input")
        add("MAGAZINE_EXTEND_CMD", "output")
        add("MAGAZINE_RETRACT_CMD", "output")

    if atc.get("sequence_options", {}).get("use_atc_door", False):
        add("ATC_DOOR_OPEN", "input")
        add("ATC_DOOR_CLOSED", "input")
        add("ATC_DOOR_OPEN_CMD", "output")
        add("ATC_DOOR_CLOSE_CMD", "output")

    drawbar = atc["transfer"].get("drawbar", {})
    if drawbar.get("type") == "pneumatic" and drawbar.get("require_air_pressure", True):
        add("AIR_PRESSURE_OK", "input", "conditional")
    if drawbar.get("verification_method") == "approved_alternative":
        add("TOOL_RETENTION_VERIFICATION", "input", "conditional")

    spindle = atc["spindle_orientation"]
    backend = spindle["backend"]
    interface = spindle["command_interface"]
    if backend == "servo_native_fixed" and interface in ("digital_io_fixed_angle", "preset_select"):
        add("SPINDLE_ORIENT_CMD", "output")
        add("SPINDLE_ORIENT_IN_POSITION", "input")
        add("SPINDLE_DRIVE_READY", "input")
        add("SPINDLE_DRIVE_FAULT", "input")
        if spindle.get("require_zero_speed", True):
            add("SPINDLE_ZERO_SPEED", "input", "conditional")
        if spindle.get("require_brake_feedback", False):
            add("SPINDLE_BRAKE_ENGAGED", "input")
    elif backend in ("servo_native_fieldbus", "external_controller"):
        # Status and commands travel over the declared communication resource.
        # A future profile may explicitly add hardwired status signals.
        pass

    disabled = set(atc.get("disabled_signals", []))
    for item in signals.values():
        if item["direction"] == "input" and item["id"] in disabled:
            item["disabled"] = True
    return sorted(
        signals.values(),
        key=lambda item: (item["direction"], _REQUIREMENT_RANK[item["requirement"]], item["id"]),
    )
