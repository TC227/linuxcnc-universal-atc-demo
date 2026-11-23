# Software 04 — รูปแบบไฟล์ Configuration

สถานะ: **DRAFT — ตัวอย่างโครงสร้างเพื่ออธิบายแนวคิดเท่านั้น**

## ข้อกำหนด

ไฟล์ Configuration ใช้ JSON และควรจัดเก็บข้อมูลต่อไปนี้:

- Schema Version
- ตัวตนของ Hardware และ Firmware
- Profile ID และ Version
- การ Mapping ระหว่าง Physical I/O กับ Logical Signal
- การตั้งค่าทางไฟฟ้าที่ Hardware รองรับ
- ค่าการสอบเทียบ Indexing
- Timeout ของแต่ละขั้นตอน
- ผลการ Validation
- ข้อมูล Backup และแนวทาง Migration เมื่อเปลี่ยน Schema Version

## ตัวอย่าง Configuration

```json
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
```

ตัวอย่างนี้ไม่ใช่ Schema ที่ผ่านการตรวจสอบ และไม่ใช่ Pinout ของบอร์ดจริง

## กฎการตรวจสอบ Configuration

- Schema Version ต้องเป็นรุ่นที่ระบบรองรับ
- Logical Signal ที่จำเป็นต้องถูก Mapping ครบ
- ห้ามกำหนด Physical Channel เดียวกันให้หลายหน้าที่ที่ขัดแย้งกัน
- Channel ที่เลือกต้องมีอยู่ใน Hardware Capability Manifest
- Electrical Mode ต้องรองรับโดยวงจรจริง
- จำนวน Pocket ต้องถูกต้องตาม ATC Profile
- Encoder Scale และ Tolerance ต้องอยู่ในช่วงที่กำหนด
- ห้ามแทน Feedback ที่จำเป็นด้วยการคาดเดาจาก Timer โดยไม่ระบุข้อจำกัด
- Profile Version ต้องเข้ากันได้กับ Configuration

## ข้อมูลอ้างอิงและที่มา (Provenance)

ควรบันทึกวันเวลาที่สร้างและแก้ไข Application Version, Board Revision, Firmware Identifier/Hash, Profile Version, ผล Validation และบันทึกการ Commissioning

**ห้ามจัดเก็บ Credential หรือรหัสผ่านไว้ใน Machine Configuration**

## รูปแบบ I/O Mapping

Configuration ต้องจัดเก็บ Mapping แยกตาม Logical Signal และ Resource Type โดยอ้างอิง Hardware Capability Manifest, Resource Reservation, HAL/Driver Endpoint และ Electrical Capability

ดูแนวทางการจัดสรร I/O ใน [Configuration Engine V1](../docs/CONFIGURATION-ENGINE-V1.md) ห้ามเก็บเพียงชื่อ DI/DO โดยไม่มี Manifest Identity และ Verification Status

## สถานะ Review และ Apply

ต้องแยกวงจรชีวิตของ Configuration ออกจาก ATC Runtime State:

`DRAFT → VALIDATED → APPLY_PENDING → APPLIED_DISABLED → COMMISSIONING → READY_TO_ENABLE → ENABLED`

และต้องรองรับสถานะ `APPLY_FAILED` กับ `ROLLED_BACK` สำหรับกรณีผิดพลาด

รายละเอียด Workflow การตรวจสอบ การสร้าง Candidate, Backup, Staging, Diff, Post-load Verification และ Commissioning ให้อ้างอิง [GUI Configuration Flow V1](05-GUI-CONFIGURATION-FLOW-V1.md)

ห้ามตีความว่า `VALIDATED` หรือ `APPLIED_DISABLED` หมายถึง ATC ผ่าน Commissioning หรือพร้อมทำ M6 แล้ว
