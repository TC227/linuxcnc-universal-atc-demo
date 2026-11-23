# สถาปัตยกรรมซอฟต์แวร์ ATC

สถานะ: **DRAFT**

## 1. องค์ประกอบหลัก

### QtVCP ATC Configurator
จัดการ Profile Wizard, DI/DO Mapping, Machine Parameters, Calibration, Diagnostics, Backup/Restore และ Validation

### Configuration Manager
อ่าน JSON แบบมี Version, ตรวจ Schema และ Hardware Capability, ตรวจ Pin ซ้ำ, ตรวจ Required Signal, สร้าง/ติดตั้ง Configuration ผ่านขั้นตอนควบคุม และเก็บ Configuration รุ่นก่อนหน้าไว้ Rollback

### HAL Abstraction
Map Physical HAL Pin เป็น Logical ATC Signal, ปรับ Active Polarity และส่งสถานะ Diagnostics โดย Filter/Debounce ต้องใช้เฉพาะส่วนที่ Hardware รองรับจริง

### ATC Manager
ควบคุม State Machine, Sequence, Timeout, Fault, Tool-change Transaction, Recovery และ Event Log

### LinuxCNC Integration
เชื่อม M6/Remap, Tool Prepare/Change Handshake และ Spindle Orientation Request/Complete

## 2. แยก Configuration ออกจาก Runtime

GUI ใช้แก้และบันทึก Configuration เท่านั้น Runtime Controller ต้องทำงานต่อได้แม้ GUI ปิดไปแล้ว ATC Manager และ HAL Configuration ต้องยังทำงานตามปกติ

## 3. การแบ่ง Real-time Boundary

พิจารณาแต่ละหน้าที่ว่าจะอยู่ใน Real-time HAL Component, Non-real-time Userspace Service หรือ External PLC การควบคุม Motion ที่ต้องการ Timing แม่นยำไม่ควรพึ่ง GUI Event Loop และ Safety-rated Function ต้องอยู่ใน Hardware Safety ที่เหมาะสม

## 4. วงจร Apply Configuration

1. โหลด Configuration ปัจจุบัน
2. ตรวจ Schema และ Hardware Capability
3. แสดง Signal ที่ขาด Pin ซ้ำ หรือการกำหนดที่ขัดแย้ง
4. บันทึก Candidate Configuration
5. สร้าง HAL/Profile Configuration
6. ตรวจ Syntax และ Dependency
7. Apply ในสภาวะเครื่องหยุดอย่างควบคุม; Restart LinuxCNC หากเปลี่ยน Module/Pin Topology
8. ตรวจ Required Signal หลังโหลด
9. เปิดใช้ ATC เมื่อผ่านการตรวจสอบทั้งหมด
10. เก็บ Configuration เดิมไว้ Rollback

## 5. Event Log

บันทึก Timestamp, Cycle ID, Tool/Pocket ที่ร้องขอ, Profile/Config Version, State Transition, Sensor ที่เกี่ยวข้อง, Output Command, Fault Code และผลลัพธ์ ไม่บันทึกข้อมูลลับหรือข้อมูลที่ไม่เกี่ยวกับการทำงาน


## 6. Review / Validate / Apply Transaction

Configuration Manager ต้องสร้าง Candidate ใน Staging, Validate กับ Hardware Capability Manifest และ Machine State, แสดง Diff, Backup Managed Files, ติดตั้งแบบควบคุม, Post-load Verify และ Rollback ได้ตาม [GUI Configuration Flow V1](05-GUI-CONFIGURATION-FLOW-V1.md) และ [Configuration Engine V1](../docs/CONFIGURATION-ENGINE-V1.md). Apply สำเร็จแล้ว ATC ต้องคง Disabled จนผ่าน Commissioning และ Operator Enable แยกต่างหาก
