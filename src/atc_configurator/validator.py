"""Configuration and hardware capability validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .profiles import find_profile, required_signal_specs


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _schema_errors(instance: dict[str, Any], schema_path: str | Path) -> list[str]:
    validator = Draft202012Validator(_load_json(schema_path))
    return [
        f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(map(str, item.absolute_path)))
    ]


def validate_configuration(
    config: dict[str, Any],
    manifest: dict[str, Any],
    profile_catalog: dict[str, Any],
    config_schema_path: str | Path,
    manifest_schema_path: str | Path,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def add(code: str, severity: str, message: str, affects: str = "configuration",
            path: str = "", page: int | None = None, resource_id: str | None = None) -> None:
        item: dict[str, Any] = {
            "id": code, "severity": severity, "message_th": message, "affects": affects
        }
        if path:
            item["path"] = path
        if page is not None:
            item["go_to_page"] = page
        if resource_id:
            item["resource_id"] = resource_id
        findings.append(item)

    config_errors = _schema_errors(config, config_schema_path)
    manifest_errors = _schema_errors(manifest, manifest_schema_path)
    for error in config_errors:
        add("CONFIG_SCHEMA_INVALID", "error", f"รูปแบบ Configuration ไม่ถูกต้อง: {error}", path="atc", page=8)
    for error in manifest_errors:
        add("HARDWARE_MANIFEST_INVALID", "blocker", f"Hardware Manifest ไม่ถูกต้อง: {error}", "apply", "hardware", 1)
    if config_errors or manifest_errors:
        return _report(config, findings)

    if config["hardware"]["manifest_id"] != manifest["manifest_id"]:
        add("HARDWARE_MANIFEST_ID_MISMATCH", "blocker", "Manifest ID ใน Configuration ไม่ตรงกับ Hardware Manifest ที่นำมาตรวจ", "apply", "hardware.manifest_id", 1)
    if manifest["status"] != "verified":
        add("HARDWARE_NOT_VERIFIED", "blocker", "Hardware Manifest ยังไม่ผ่านการยืนยันกับบอร์ด, Revision, Firmware และวงจรจริง จึงห้าม Apply ลงเครื่องจริง", "apply", "hardware", 1)
    else:
        identity = manifest["identity"]
        identity_values = (
            identity["controller_profile"], identity["board_revision"],
            identity["hostmot2_firmware_id"], identity["linuxcnc_version"],
        )
        if any(not value.strip() or value.strip().upper() == "UNCONFIRMED" for value in identity_values) or not identity.get("hostmot2_firmware_sha256"):
            add("HARDWARE_IDENTITY_INCOMPLETE", "blocker", "Manifest ที่ระบุว่า Verified ต้องมี Board Revision, HostMot2 Firmware ID/Hash และ LinuxCNC Version ที่ตรวจสอบแล้ว", "apply", "identity", 1)

    profile = find_profile(profile_catalog, config["atc"]["profile_id"])
    if profile is None:
        add("PROFILE_NOT_FOUND", "error", "ไม่พบ ATC Profile ที่เลือกใน Profile Catalog", path="atc.profile_id", page=2)
        return _report(config, findings)

    atc = config["atc"]
    magazine = atc["magazine"]
    if magazine["type"] != profile["magazine_type"]:
        add("PROFILE_MAGAZINE_MISMATCH", "error", "ชนิด Magazine ไม่ตรงกับ Profile ที่เลือก", path="atc.magazine.type", page=2)
    bounds = profile["pocket_count"]
    if not bounds["min"] <= magazine["pocket_count"] <= bounds["max"]:
        add("POCKET_COUNT_OUT_OF_RANGE", "error", f"จำนวน Pocket ต้องอยู่ระหว่าง {bounds['min']} ถึง {bounds['max']} ตาม Profile Catalog รุ่นนี้", path="atc.magazine.pocket_count", page=3)
    reference_pocket = magazine.get("reference_pocket", 1)
    if not 1 <= reference_pocket <= magazine["pocket_count"]:
        add("REFERENCE_POCKET_OUT_OF_RANGE", "error", "Reference Pocket ต้องอยู่ในช่วง 1 ถึงจำนวน Pocket", path="atc.magazine.reference_pocket", page=3)
    if magazine.get("direction_policy") == "shortest_path" and not magazine.get("reversible", False):
        add("SHORTEST_PATH_REQUIRES_REVERSIBLE_DRIVE", "error", "Shortest Path ใช้ได้เมื่อ Drive กลับทิศทางได้เท่านั้น", path="atc.magazine.direction_policy", page=3)
    if magazine["type"] == "linear_rack" and not magazine.get("linear_pitch_mm"):
        add("LINEAR_RACK_PITCH_REQUIRED", "error", "Linear Rack ต้องกำหนดระยะ Pitch ต่อ Pocket มากกว่า 0 mm", path="atc.magazine.linear_pitch_mm", page=3)

    feedback_method = magazine["position_feedback"]["method"]
    if feedback_method not in profile["supported_position_feedback"]:
        add("FEEDBACK_METHOD_UNSUPPORTED", "error", "Profile นี้ไม่รองรับวิธีตรวจตำแหน่ง Magazine ที่เลือก", path="atc.magazine.position_feedback.method", page=5)
    if feedback_method == "open_loop_step_count":
        add("OPEN_LOOP_POSITIONING_LIMITATION", "warning", "Open-loop Step Count เป็นค่าประมาณตำแหน่ง ไม่ใช่ Feedback ยืนยันตำแหน่งจริง ต้องมี Homing และห้าม Resume เมื่อ Position Unknown", "enable_atc", "atc.magazine.position_feedback.method", 5)

    transfer = atc["transfer"]["mechanism"]
    if transfer not in profile["supported_transfer_mechanisms"]:
        add("TRANSFER_MECHANISM_UNSUPPORTED", "error", "Profile นี้ไม่รองรับกลไกส่งทูลที่เลือก", path="atc.transfer.mechanism", page=4)
    presentation = atc["transfer"].get("presentation", {}).get("mode", "fixed")
    if presentation != "fixed" and transfer not in ("direct_pickup", "pot_movement", "single_arm", "double_arm_180"):
        add("PRESENTATION_TRANSFER_MISMATCH", "error", "Presentation Motion ไม่สอดคล้องกับ Transfer Mechanism", path="atc.transfer.presentation.mode", page=4)
    drawbar = atc["transfer"].get("drawbar", {})
    if drawbar.get("verification_method") == "not_configured":
        add("DRAWBAR_VERIFICATION_MISSING", "error", "ยังไม่ได้กำหนดวิธียืนยันการจับยึด Tool ที่ Spindle", path="atc.transfer.drawbar.verification_method", page=4)
    elif drawbar.get("verification_method") == "approved_alternative":
        add("DRAWBAR_ALTERNATIVE_REQUIRES_REVIEW", "warning", "ใช้วิธียืนยัน Drawbar แบบอื่น ต้องมีหลักฐานและการอนุมัติจากผู้สร้าง Machine Profile", "enable_atc", "atc.transfer.drawbar.verification_method", 4)

    if atc["tool_management"]["location_model"] == "random":
        add("RANDOM_POCKET_RUNTIME_NOT_IMPLEMENTED", "error", "Random Pocket ยังไม่มี Runtime Tool Location Manager และ Power-loss Recovery ที่ผ่านการทดสอบ จึงยังไม่เปิดใช้ใน Wizard รุ่นนี้", path="atc.tool_management.location_model", page=3)

    resources = {item["id"]: item for item in manifest["resources"]}
    if len(resources) != len(manifest["resources"]):
        add("DUPLICATE_MANIFEST_RESOURCE_ID", "blocker", "Hardware Manifest มี Resource ID ซ้ำกัน", "apply", "resources", 1)

    mapping = atc["io_mapping"]
    specs = required_signal_specs(config, profile)
    known_signal_ids = {spec["id"] for spec in specs}
    used: dict[str, str] = {}
    for unknown_id in sorted(set(mapping) - known_signal_ids):
        add("UNKNOWN_LOGICAL_SIGNAL", "error", f"Mapping มี Logical Signal {unknown_id} ที่ไม่ได้ใช้ใน Profile/Configuration ปัจจุบัน", path=f"atc.io_mapping.{unknown_id}", page=7)
    for spec in specs:
        signal_id = spec["id"]
        if spec.get("disabled"):
            if signal_id in mapping:
                add("DISABLED_SIGNAL_MAPPED", "warning", f"สัญญาณ {signal_id} ถูกตั้งเป็นไม่ใช้ จึงข้ามการตรวจและไม่ใช้ Mapping นี้", path=f"atc.io_mapping.{signal_id}", page=7)
            continue
        mapped = mapping.get(signal_id)
        if mapped is None:
            if spec.get("requirement", "required") in ("required", "conditional"):
                add("REQUIRED_SIGNAL_UNMAPPED", "error", f"ยังไม่ได้กำหนด Physical I/O ให้สัญญาณ {signal_id}", path=f"atc.io_mapping.{signal_id}", page=7)
            continue
        resource_id = mapped["resource_id"]
        resource = resources.get(resource_id)
        if resource is None:
            add("RESOURCE_NOT_FOUND", "error", f"ไม่พบ Resource {resource_id} ใน Hardware Manifest", path=f"atc.io_mapping.{signal_id}", page=7, resource_id=resource_id)
            continue
        expected_type = "digital_input" if spec["direction"] == "input" else "digital_output"
        if resource["type"] != expected_type:
            add("RESOURCE_DIRECTION_MISMATCH", "error", f"{signal_id} ต้องใช้ {expected_type} แต่เลือก {resource['type']}", path=f"atc.io_mapping.{signal_id}", page=7, resource_id=resource_id)
        if not resource["available"] or resource.get("status", "available") != "available":
            add("RESOURCE_NOT_AVAILABLE", "error", f"Resource {resource_id} ไม่พร้อมใช้งานหรือถูกจองไว้", path=f"atc.io_mapping.{signal_id}", page=7, resource_id=resource_id)
        if resource.get("reserved_by"):
            add("RESOURCE_RESERVED", "error", f"Resource {resource_id} ถูกใช้งานโดย {resource['reserved_by']} อยู่แล้ว", path=f"atc.io_mapping.{signal_id}", page=7, resource_id=resource_id)
        if not resource["verified"]:
            add("RESOURCE_NOT_VERIFIED", "blocker", f"Resource {resource_id} ยังไม่ได้ยืนยันกับ Hardware จริง", "apply", f"atc.io_mapping.{signal_id}", 7, resource_id)
        if resource_id in used:
            add("RESOURCE_CONFLICT", "error", f"Resource {resource_id} ถูกใช้ซ้ำโดย {used[resource_id]} และ {signal_id}", path=f"atc.io_mapping.{signal_id}", page=7, resource_id=resource_id)
        else:
            used[resource_id] = signal_id
        supported_levels = resource.get("electrical", {}).get("supported_active_levels")
        if supported_levels and mapped["active_level"] not in supported_levels:
            add("ELECTRICAL_ACTIVE_LEVEL_UNSUPPORTED", "error", f"Resource {resource_id} ไม่รองรับ Active Level {mapped['active_level']}", path=f"atc.io_mapping.{signal_id}", page=7, resource_id=resource_id)

    motion = atc.get("motion_resources", {})
    drive_interface = magazine["drive"]["interface"]
    if drive_interface == "stepgen":
        _check_resource(add, resources, motion.get("magazine_motion"), "stepgen", "MAGAZINE_STEPGEN_MISSING", "Magazine ต้องใช้ Stepgen แต่ยังไม่ได้เลือก Resource ที่ถูกต้อง", 7)
    elif drive_interface in ("fieldbus", "external_controller"):
        _check_resource(add, resources, motion.get("magazine_motion"), "communication", "MAGAZINE_COMMUNICATION_MISSING", "Magazine ต้องใช้ Communication Resource แต่ยังไม่ได้เลือก Resource ที่ถูกต้อง", 7)

    if feedback_method in ("incremental_encoder", "absolute_encoder"):
        encoder_id = magazine["position_feedback"].get("encoder_resource_id") or motion.get("magazine_position_encoder")
        _check_resource(add, resources, encoder_id, "encoder", "MAGAZINE_ENCODER_MISSING", "วิธีตรวจตำแหน่งที่เลือกต้องใช้ Encoder Resource", 5)

    spindle = atc["spindle_orientation"]
    backend = spindle["backend"]
    interface = spindle["command_interface"]
    spindle_resources = spindle.get("resources", {})
    allowed_interfaces = {
        "servo_native_fixed": ("digital_io_fixed_angle", "preset_select"),
        "servo_native_fieldbus": ("fieldbus_register",),
        "linuxcnc_encoder_pid": ("linuxcnc_m19",),
        "external_controller": ("serial_command", "fieldbus_register", "pulse_direction", "analog_position"),
    }
    if interface not in allowed_interfaces[backend]:
        add("M19_BACKEND_INTERFACE_MISMATCH", "error", "M19 Backend ไม่รองรับ Command Interface ที่เลือก", path="atc.spindle_orientation.command_interface", page=6)
    if spindle["target_mode"] == "fixed" and "fixed_angle_deg" not in spindle:
        add("M19_FIXED_ANGLE_MISSING", "error", "เลือก Fixed Target แต่ยังไม่ได้กำหนดมุม M19", path="atc.spindle_orientation.fixed_angle_deg", page=6)
    if backend == "linuxcnc_encoder_pid":
        _check_resource(add, resources, spindle_resources.get("encoder_resource_id"), "encoder", "SPINDLE_ENCODER_MISSING", "LinuxCNC Encoder/PID ต้องมี Spindle Encoder Resource", 6)
    elif backend in ("servo_native_fieldbus", "external_controller") and interface in ("fieldbus_register", "serial_command"):
        _check_resource(add, resources, spindle_resources.get("communication_resource_id"), "communication", "SPINDLE_COMMUNICATION_MISSING", "M19 Backend ต้องมี Communication Resource ที่ตรงกับ Protocol", 6)
    elif interface == "pulse_direction":
        _check_resource(add, resources, spindle_resources.get("position_command_resource_id"), "stepgen", "SPINDLE_POSITION_COMMAND_MISSING", "Pulse/Direction Orientation ต้องมี Position Stepgen Resource", 6)
    elif interface == "analog_position":
        _check_resource(add, resources, spindle_resources.get("position_command_resource_id"), "dac", "SPINDLE_ANALOG_POSITION_MISSING", "Analog Position ต้องมี DAC Resource ที่ Drive รองรับ", 6)

    return _report(config, findings)


def _check_resource(
    add: Any, resources: dict[str, dict[str, Any]], resource_id: str | None,
    expected_type: str, code: str, message: str, page: int,
) -> None:
    if not resource_id or resource_id not in resources:
        add(code, "error", message, path="atc.motion_resources", page=page)
        return
    resource = resources[resource_id]
    if resource["type"] != expected_type or not resource["available"] or resource.get("status", "available") != "available":
        add(code, "error", f"{message} (Resource {resource_id} ไม่ตรงชนิดหรือไม่พร้อมใช้งาน)", path="atc.motion_resources", page=page, resource_id=resource_id)
    elif resource.get("reserved_by"):
        add("RESOURCE_RESERVED", "error", f"Resource {resource_id} ถูกใช้งานโดย {resource['reserved_by']} อยู่แล้ว", path="atc.motion_resources", page=page, resource_id=resource_id)
    elif not resource["verified"]:
        add("RESOURCE_NOT_VERIFIED", "blocker", f"Resource {resource_id} ยังไม่ได้ยืนยันกับ Hardware จริง", "apply", "atc.motion_resources", page, resource_id)


def _report(config: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        level: sum(1 for item in findings if item["severity"] == level)
        for level in ("blocker", "error", "warning", "info")
    }
    configuration_valid = summary["error"] == 0
    live_apply_allowed = configuration_valid and summary["blocker"] == 0
    return {
        "report_version": 1,
        "config_id": config.get("config_id", "unknown"),
        "configuration_valid": configuration_valid,
        "live_apply_allowed": live_apply_allowed,
        "summary": summary,
        "findings": findings,
        "decisions": {
            "save_draft": True,
            "validate": configuration_valid,
            "apply_live": live_apply_allowed,
            "enable_atc": False,
        },
    }
