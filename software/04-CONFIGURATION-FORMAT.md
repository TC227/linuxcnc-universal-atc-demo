# Software 04 — Configuration Format

สถานะ: DRAFT — illustrative schema only.

## Requirements

JSON with schema version, hardware/firmware identity, profile ID/version, physical-to-logical mapping, supported electrical settings, indexing calibration, timeouts, validation result, backup and migration support.

## Illustrative configuration

    {
      "schema_version": 1,
      "machine": {
        "controller": "7i92-7i76-clone",
        "board_revision": "UNCONFIRMED",
        "hostmot2_firmware": "UNCONFIRMED",
        "linuxcnc_version": "2.9"
      },
      "atc": {
        "profile_id": "side-mount-double-arm",
        "profile_version": 1,
        "magazine": {
          "type": "chain",
          "pocket_count": 24,
          "index_drive": "servo",
          "position_feedback": "incremental_encoder",
          "direction_policy": "shortest_path"
        },
        "tool_management": {
          "location_model": "random"
        },
        "signals": {
          "MAG_HOME": {"source": "DI00", "active_level": "high"},
          "MAG_IN_POSITION": {"source": "DI01", "active_level": "high"},
          "ARM_HOME": {"source": "DI02", "active_level": "high"},
          "DRAWBAR_CLAMPED": {"source": "DI03", "active_level": "high"},
          "MAG_CW": {"source": "DO00", "active_level": "high"},
          "MAG_CCW": {"source": "DO01", "active_level": "high"}
        },
        "spindle_orientation": {
          "linuxcnc_interface": "m19",
          "backend": "servo_drive_native",
          "command_interface": "digital_io_fixed_angle",
          "target_mode": "fixed",
          "fixed_angle_deg": 180.0,
          "in_position_signal": "SPINDLE_ORIENT_IN_POSITION",
          "drive_ready_signal": "SPINDLE_DRIVE_READY",
          "drive_fault_signal": "SPINDLE_DRIVE_FAULT"
        },
        "timeouts_ms": {
          "magazine_home": 15000,
          "magazine_index": 10000,
          "spindle_orient": 8000,
          "tool_exchange": 12000
        }
      }
    }

This is not a validated schema or a real board pinout.

## Validation

- schema version supported
- every required signal mapped
- no physical channel assigned to conflicting functions
- selected channel exists in hardware capability manifest
- electrical mode supported by the actual circuit
- pocket count valid for profile
- encoder scale/tolerance valid
- required feedback not silently replaced by timer assumptions
- profile version compatible

## Provenance

Store created/modified timestamp, application version, board revision, firmware identifier/hash, profile version, validation result and commissioning notes. Never store credentials in machine configuration.


## I/O Mapping Model

Configuration ต้องเก็บ Mapping แยกตาม Logical Signal และ Resource Type โดยอ้างอิง Hardware Capability Manifest, Resource Reservation, HAL/Driver Endpoint และ Electrical Capability ตาม [I/O Mapping & Automatic Assignment Screen V1](11-IO-MAPPING-SCREEN-V1.md) ห้ามเก็บเฉพาะชื่อ DI/DO โดยไม่มี Manifest Identity และ Verification Status


## Review / Apply State Model

ให้แยก Configuration Lifecycle ออกจาก ATC Runtime State: DRAFT → VALIDATED → APPLY_PENDING → APPLIED_DISABLED → COMMISSIONING → READY_TO_ENABLE → ENABLED โดยมี APPLY_FAILED และ ROLLED_BACK สำหรับกรณีผิดพลาด รายละเอียด Validation Report, Apply Journal, Backup, Staging, Diff, Post-load Verification และ Commissioning อยู่ใน [Review, Validate & Apply Screen V1](12-REVIEW-VALIDATE-APPLY-SCREEN-V1.md)

ห้ามถือว่า VALIDATED หรือ APPLIED_DISABLED หมายถึง ATC ผ่าน Commissioning หรือพร้อมทำ M6 แล้ว
