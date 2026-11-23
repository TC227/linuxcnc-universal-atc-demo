# ATC State Machine — ลำดับสถานะการทำงาน

สถานะ: **DRAFT**

## 1. สถานะหลัก

- DISABLED — ปิด ATC
- IDLE — พร้อมรับคำสั่ง
- PRECHECK — ตรวจเงื่อนไขก่อนเริ่ม
- TOOL_PREPARE — เตรียมข้อมูล Tool/Pocket
- MAGAZINE_INDEX — หมุน Magazine
- VERIFY_MAGAZINE — ตรวจตำแหน่ง Magazine
- SPINDLE_STOP — หยุด Spindle
- SPINDLE_ORIENT — จัดตำแหน่งด้วย M19
- EXCHANGE_PREPARE — เตรียมกลไกแลกทูล
- DRAWBAR_UNCLAMP — ปลด Drawbar
- TOOL_TRANSFER — แลกทูล
- DRAWBAR_CLAMP — จับทูล
- VERIFY_TOOL — ตรวจ Tool Presence/Clamp
- RETURN_MECHANISM — คืนแขน/Pot/Magazine
- COMMIT_TOOL_LOCATION — บันทึกตำแหน่งทูลใหม่
- COMPLETE — แจ้งสำเร็จ
- FAULT — เกิดข้อผิดพลาด
- RECOVERY_REQUIRED — ต้องกู้คืน
- MANUAL_RECOVERY — กู้คืนด้วยผู้ปฏิบัติงาน

แต่ละ Profile ไม่จำเป็นต้องใช้ทุก State และต้องตรวจความถูกต้องของลำดับก่อนเปิดใช้งาน

## 2. ตัวอย่างลำดับการทำงาน

1. รับคำขอ Tool Change จาก LinuxCNC
2. ตรวจ Tool และ Pocket Mapping
3. ตรวจว่าเครื่องอยู่ในสถานะที่อนุญาต
4. เคลื่อน Magazine ไปยัง Pocket เป้าหมาย
5. ยืนยันตำแหน่ง Magazine
6. หยุด Spindle และสั่ง M19 หากจำเป็น
7. ตรวจ Spindle Stop/Orient และ Interlock ของการแลกทูล
8. เคลื่อน Pot/Arm/Gripper เข้าตำแหน่ง
9. ตรวจการจับทูลเก่าและทูลใหม่
10. ปลด/แลก/จับ Drawbar ตามลำดับเฉพาะกลไก
11. ตรวจ Tool Presence และ Clamp
12. คืนกลไกไปตำแหน่งปลอดภัย
13. Commit Tool Location
14. แจ้ง LinuxCNC ว่าเปลี่ยนทูลเสร็จ

## 3. สัญญาของแต่ละ Transition

ทุก Transition ต้องระบุ Entry Condition, Output Command, Expected Sensor, Timeout, Success Condition, Fault Code, Safe Response และ Recovery Instruction

## 4. ตัวอย่าง Fault

AIR_PRESSURE_LOW, SPINDLE_NOT_STOPPED, ORIENTATION_TIMEOUT, SPINDLE_DRIVE_NOT_READY, SPINDLE_DRIVE_ALARM, SPINDLE_ORIENT_IN_POSITION_MISSING, SPINDLE_ORIENT_ANGLE_MISMATCH, SPINDLE_ORIENT_MODE_UNSUPPORTED, SPINDLE_ORIENT_PRESET_NOT_MAPPED, SPINDLE_ORIENT_COMMUNICATION_LOSS, SPINDLE_ENCODER_FAULT, SPINDLE_POSITION_TOLERANCE_EXCEEDED, SPINDLE_BRAKE_NOT_CONFIRMED, MAG_HOME_NOT_FOUND, MAG_POSITION_MISMATCH, MAG_POSITION_UNSTABLE, MAG_INVALID_POSITION_CODE, MAG_ENCODER_FAULT, MAG_FOLLOWING_ERROR, MAG_IN_POSITION_TIMEOUT, MAG_REFERENCE_LOST, MAG_MECHANICAL_LOCK_NOT_CONFIRMED, ARM_POSITION_TIMEOUT, GRIPPER_NOT_CLOSED, TOOL_NOT_PRESENT, DRAWBAR_STATE_MISMATCH, DRIVE_FAULT, SENSOR_CONTRADICTION, CONFIGURATION_INVALID และ TOOL_LOCATION_UNKNOWN

## 5. กฎบังคับ

- การสั่ง Output ไม่ใช่หลักฐานว่ากลไกเคลื่อนที่สำเร็จ
- ห้ามข้าม Sensor Verification ที่ล้มเหลวโดยอัตโนมัติ
- ห้าม Commit Random Pocket ก่อนตรวจสอบการแลกทูลทางกายภาพ
- หลังไฟดับ ให้ State ที่ยังไม่ได้ตรวจเป็น UNKNOWN
- Recovery ต้องเป็นขั้นตอนที่ชัดเจนและผู้ปฏิบัติงานรับทราบ
- การปิด GUI ต้องไม่ทำให้ Sequence Controller หยุดทำงานกลางคัน
