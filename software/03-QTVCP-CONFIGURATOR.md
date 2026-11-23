# ตัวตั้งค่า ATC ผ่าน QtVCP

สถานะ: **DRAFT — GUI-first**

## เป้าหมาย

เพิ่ม ATC Tab/Panel ใน QtVCP/Axis เดิม โดยไม่บังคับให้เปลี่ยน GUI CNC หลัก ผู้ใช้ทั่วไปต้องตั้งค่า ATC ผ่าน Wizard ได้โดยไม่ต้องเปิดแก้ไข HAL/INI ด้วยตนเอง

รายละเอียดหน้าจอและลำดับการตั้งค่าอ้างอิง:
[GUI Configuration Flow V1](05-GUI-CONFIGURATION-FLOW-V1.md)

## Hardware Reference

- Main Reference: 7i92 + 1x 7i76
- Expansion Candidate: 7i92 + 2x 7i76 เฉพาะเมื่อยืนยัน HostMot2/Bitfile, Connector Topology และ SmartSerial Mapping
- GUI ต้องใช้ Hardware Capability Manifest เป็นแหล่งข้อมูลว่ามี DI/DO, Encoder, Stepgen และ Interface ใดใช้ได้จริง
- I/O Matrix เป็น Logical Requirement Reference ไม่ใช่ Pinout หรือข้อกำหนดให้ทำ PCB ใหม่

## ATC รุ่นแรก

1. Umbrella / Parasol
2. Rotary Disc / Carousel
3. Side-mounted + Double Arm
4. Chain Magazine
5. Linear Rack

Turret, Matrix/Shelf, Multi-Magazine และ Robot เป็น Future Extension

## หน้าจอหลัก

### Overview
แสดง Profile, Current/Next Tool, Pocket, Magazine Position, ATC State, Spindle State, Interlock Summary และ Active Fault

### Setup Wizard
ลำดับการตั้งค่า:
1. Hardware/Controller
2. ATC Type
3. Magazine Parameters
4. Transfer Mechanism
5. Position Feedback และ Calibration
6. Spindle Orientation/M19
7. I/O Mapping
8. Review/Validate/Apply

Sequence Options และ Timeout ที่ผู้ใช้ทั่วไปต้องตั้งจะถูกรวมในหน้าที่เกี่ยวข้อง ส่วน Advanced Custom Sequence ยังไม่เปิดใน Basic Mode

แสดงเฉพาะค่าที่เกี่ยวข้องกับตัวเลือกก่อนหน้า

### I/O Mapping
แสดง Logical Signal, Required/Optional, Physical Channel ที่เลือกได้จริง, Polarity, Live Status และการตรวจ Pin ซ้ำ

ห้ามให้ GUI เสนอ Physical Resource ที่ไม่มีใน Hardware Manifest และห้ามเปลี่ยน Electrical Capability ที่วงจรจริงไม่รองรับ

### Calibration
Home, Teach Pocket, Offset, Pitch, Encoder Scale, Direction, Tolerance และ Verification ตามชนิด Magazine

### Diagnostics
Input Monitor, Output Test ใน Maintenance Mode, Encoder/Drive Status และ Event Log

### Recovery
แสดง State ล่าสุด, Sensor ที่ยืนยันได้, Tool Location Known/Unknown และขั้นตอน Manual Recovery

## UX Rules

- ใช้ชื่อภาษาคนอ่าน เช่น "Magazine Home Sensor" และแสดง Logical Name ประกอบ
- Auto-map ได้เฉพาะ Mapping ที่ไม่ขัดแย้งและ Hardware รองรับ
- ซ่อนค่าที่ไม่เกี่ยวข้องกับ Profile
- แยก Required, Optional และ Conditional
- แยก Live Hardware ออกจาก Simulation ให้ชัดเจน
- ตรวจ Resource Conflict และ Missing Feedback ก่อน Apply
- Advanced Custom Sequence ไม่อยู่ใน Basic Mode รุ่นแรก

## Apply Workflow

Stop/Disable ATC → Validate → แสดง Error/Warning และ Configuration Diff → Backup → Generate Configuration → Apply/Restart เมื่อจำเป็น → Post-load Diagnostics → Enable

ถ้า Apply ไม่สำเร็จต้อง Rollback ได้

## Runtime Boundary

GUI ทำหน้าที่ตั้งค่าและแสดงสถานะ ไม่ใช่ตัวควบคุม Sequence แบบ Real-time การปิดหน้าต่าง GUI ต้องไม่หยุด ATC Runtime กลาง Cycle

Output Test ต้องตรวจ Machine State และ Interlock ก่อน และไม่ใช่ Safety Function

## สถานะ

เอกสารนี้เป็นข้อกำหนด UX/Workflow ยังไม่ใช่ GUI ที่ Implemented และยังไม่รับรอง Hardware Capability ของ 7i92 + 7i76 หรือ 7i76 สองชุด


## รายละเอียดหน้าจอ Wizard

ลำดับหน้าจอทั้ง 8 ขั้นตอน ตั้งแต่เลือก Hardware, ATC Type, Magazine, Transfer, Position Feedback, M19, I/O Mapping จนถึง Review/Validate/Apply อธิบายไว้ใน [GUI Configuration Flow V1](05-GUI-CONFIGURATION-FLOW-V1.md)

การตรวจ Hardware Manifest, การจัดสรร Resource, การตรวจ Configuration และการสร้าง Candidate อธิบายเพิ่มเติมใน [Configuration Engine V1](../docs/CONFIGURATION-ENGINE-V1.md) และ [รูปแบบไฟล์ Configuration](04-CONFIGURATION-FORMAT.md)
