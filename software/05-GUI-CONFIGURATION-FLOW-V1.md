# ลำดับการตั้งค่า GUI V1

สถานะ: **DRAFT — ข้อกำหนด UX/Workflow ก่อนพัฒนา QtVCP**

วันที่: 16 พฤศจิกายน 2026

## 1. ทิศทางโครงการ

โครงการจะพัฒนา **GUI Configurator และ ATC Software ก่อนการออกแบบ PCB ใหม่** โดยยึดบอร์ดที่มีอยู่เป็น Hardware Reference:

- ฐานหลัก: Ethernet FPGA Controller ตระกูล 7i92 + 7i76 จำนวน 1 ชุด
- ทางเลือกขยาย: 7i92 + 7i76 จำนวน 2 ชุด เมื่อยืนยันว่า Connector Topology, HostMot2 Bitfile และ SmartSerial/Pin Mapping รองรับจริง
- GUI ต้องอ่านหรือรับรอง Hardware Capability Manifest ก่อนแสดง Resource ที่เลือกได้
- ไม่สมมติว่าการต่อ 7i76 สองชุดจะทำงานได้โดยอัตโนมัติ และไม่สมมติจำนวน DI/DO, Stepgen หรือ Encoder จนกว่าจะตรวจ Bitfile/HostMot2 จริง
- เอกสาร I/O Matrix ใช้เป็นรายการอ้างอิง Logical Signal เท่านั้น ไม่ใช่คำสั่งให้ออกแบบ PCB หรือกำหนด Pinout ในขั้นตอนนี้

**หลักการ:** ลูกค้าตั้งค่าผ่าน GUI โดยไม่ต้องแก้ HAL/INI ด้วยตนเอง โปรแกรมเป็นผู้ตรวจสอบและสร้าง Configuration ที่จำเป็นให้

## 2. ขอบเขต ATC รุ่นแรก

เริ่มจากกลไกที่พบได้ทั่วไป 5 รูปแบบ:

1. Umbrella / Parasol
2. Rotary Disc / Carousel
3. Side-mounted Magazine + Double Arm
4. Chain Magazine
5. Linear Rack

ยังไม่ทำ GUI สำหรับ Turret, Matrix/Shelf, Multi-Magazine หรือ Robot Warehouse ในรุ่นแรก ให้เก็บเป็น Future Extension

รูปแบบ Magazine และ Transfer Mechanism ต้องแยกจากกัน เช่น Rotary Disc อาจใช้ Direct Pickup หรือ Double Arm ได้ ไม่ควรผูก GUI ให้เลือกได้เพียงชุดค่าตายตัวชุดเดียว

## 3. โครงสร้างหน้าจอหลัก

เพิ่ม Tab หรือ Panel ชื่อ **ATC** ใน QtVCP/Axis เดิม โดยไม่บังคับให้เปลี่ยน GUI CNC หลัก

แถบนำทางหลัก:

- **Overview** — สถานะ ATC และ Tool ปัจจุบัน
- **Setup Wizard** — ตั้งค่าเครื่องครั้งแรกและแก้ Configuration
- **I/O Monitor** — ตรวจ Sensor, Output และการ Mapping
- **Calibration** — Home, Teach Pocket และตรวจตำแหน่ง
- **Diagnostics** — Event Log, Fault และ Drive/Encoder Status
- **Recovery** — ขั้นตอนกู้คืนหลัง Fault หรือไฟดับ

หน้าปฏิบัติงานปกติควรแสดง Tool ปัจจุบัน, Tool เป้าหมาย, Pocket, Magazine Position, ATC State, Interlock Summary และ Fault ที่กำลังเกิด

## 4. Setup Wizard — ลำดับหน้าคอนฟิก

**ลำดับที่ผู้ใช้เห็นมี 8 หน้า:** 1 Hardware, 2 ATC Type, 3 Magazine, 4 Transfer, 5 Feedback, 6 M19, 7 I/O Mapping และ 8 Review/Validate/Apply. Sequence Options แสดงในหน้าที่เกี่ยวข้องตาม Profile ไม่เพิ่มเป็นหน้าที่ 9. Calibration/Diagnostics/Recovery เป็นงาน Commissioning และ Operation หลัง Setup.

### Wizard Page 1 — Hardware / Controller

ให้ผู้ใช้เลือกหรือตรวจสอบ Hardware Profile:

- 7i92 + 1x 7i76
- 7i92 + 2x 7i76 (แสดงเป็น Experimental/Unsupported จนกว่าจะยืนยัน Topology และ Firmware)
- Firmware/HostMot2 identity
- Physical DI/DO ที่ใช้งานได้จริง
- Encoder และ Stepgen Resource ที่ตรวจพบ
- SmartSerial/Expansion ที่ตรวจพบ

GUI ต้องแสดงสถานะ Resource เป็น:
- Available — ตรวจพบและยืนยันว่าใช้งานได้
- In Use — ถูกจองโดยแกน CNC, Spindle หรือฟังก์ชันอื่น
- Unsupported — Firmware/Hardware ไม่มีความสามารถนี้
- Unverified — ยังไม่มีข้อมูลยืนยัน ห้ามเสนอให้เลือกใช้งานจริง

ห้ามให้ผู้ใช้เลือกช่องที่ไม่มีอยู่จริงเพียงเพราะอยู่ในรายการมาตรฐาน

### Wizard Page 2 — ATC Type

เลือกหนึ่งในห้ารูปแบบ:
- Umbrella / Parasol
- Rotary Disc / Carousel
- Side-mounted + Double Arm
- Chain Magazine
- Linear Rack

แสดงภาพอธิบายและข้อความสั้น ๆ ว่ากลไกทำงานอย่างไร พร้อมคำถามคัดแยกที่จำเป็นเท่านั้น

### Wizard Page 3 — Magazine Setup

ตั้งค่าตามชนิดที่เลือก:
- จำนวน Pocket
- หมายเลข Pocket เริ่มต้น/จุดอ้างอิง
- ทิศทางหมุนที่อนุญาต: CW, CCW หรือทั้งสองทิศ
- นโยบายเลือกทิศทาง: ทิศที่กำหนด หรือระยะทางสั้นที่สุด (แสดงเมื่อกลไกรองรับ)
- Fixed Pocket หรือ Random Pocket
- Rotary: ระยะเชิงมุม/Offset และจำนวนช่อง
- Linear Rack: Pitch, จุดเริ่มต้น และช่วงการเคลื่อนที่

ค่าที่ไม่เกี่ยวข้องกับชนิด Magazine ต้องซ่อน ไม่ควรแสดงช่องตั้งค่าทั้งหมดพร้อมกัน

### Wizard Page 4 — Tool Transfer Mechanism

เลือกกลไกส่งทูล:
- Direct Pickup
- Pot / Magazine Movement
- Single Arm
- Double Arm 180°

GUI สร้างรายการ Sensor และ Output ที่จำเป็นจากตัวเลือกนี้โดยอัตโนมัติ ไม่ให้ผู้ใช้ต้องจำชื่อ HAL Pin เอง

กลไกที่ยังไม่รองรับใน Runtime รุ่นแรกให้แสดงเป็น Planned/Unavailable ไม่ใช่เปิดให้ตั้งค่าแล้วทำงานไม่ได้

### Wizard Page 5 — Magazine Position Feedback

เลือกวิธีที่เครื่องมีจริง:
- Home + Index Sensor
- Gray Code
- Binary / BCD
- Sensor per Pocket
- Incremental Encoder
- Absolute Encoder

เมื่อเลือกวิธีใด ให้ GUI แสดงเฉพาะพารามิเตอร์และ Logical Signal ที่เกี่ยวข้อง เช่น:
- Home Sensor และ Index Sensor
- จำนวน Code Bit และ Bit Order
- Encoder Interface, Scale, Direction และ Index/Z (เมื่อ Hardware รองรับ)
- จำนวน Sensor ต่อ Pocket

Encoder ต้องใช้ High-speed Encoder Resource ที่ตรวจสอบแล้ว ไม่ Map A/B/Z ลง DI ทั่วไปโดยพลการ

### Wizard Page 6 — Spindle Orientation (M19)

ถามก่อนว่า ATC ต้องจัดแนว Spindle หรือไม่

หากต้องใช้ M19 ให้เลือก Interface ที่ระบบรองรับ เช่น:
- Drive/Spindle Controller จัด Orientation เองและส่งสถานะ Complete
- LinuxCNC Spindle Orient Interface พร้อม Encoder/Drive Feedback

ค่าที่แสดงตาม Interface:
- Target Angle
- Direction/Approach Policy
- Position Tolerance
- Orientation Timeout
- Orient Complete / Fault Feedback

GUI ต้องแยก Spindle Stopped ออกจาก Spindle Oriented เพราะเป็นคนละเงื่อนไข และห้ามใช้ Timer เพียงอย่างเดียวแทนการยืนยันมุมจริงเมื่อเครื่องต้องการ Position Feedback

### Wizard Page 7 — I/O Mapping

แสดงตารางที่สร้างจาก Profile โดยอัตโนมัติ:

| Logical Signal | Requirement | Physical Source | Polarity | Live Status |
|---|---|---|---|---|
| MAG_HOME | Required | DI เลือกได้ | Active High/Low | ON/OFF |
| MAG_IN_POSITION | Required ตาม Feedback | DI/Encoder Status | ตาม Interface | ON/OFF |
| DRAWBAR_CLAMPED | Required ตามกลไก | DI เลือกได้ | Active High/Low | ON/OFF |
| ARM_180 | Required เมื่อใช้ Double Arm | DI เลือกได้ | Active High/Low | ON/OFF |
| MAG_CW | Required ตาม Drive | DO เลือกได้ | Active High/Low | ON/OFF |

คุณสมบัติ:
- Auto-map สัญญาณพื้นฐานให้ก่อน หาก Mapping ไม่ชนกัน
- ผู้ใช้เปลี่ยน Physical Channel ได้จากรายการช่องที่ Hardware Manifest อนุญาต
- แสดง Required, Optional และ Conditional
- ตรวจช่องซ้ำ, Signal ขาด, ช่องที่ถูกจอง และ Hardware ไม่รองรับ
- ตั้ง Active High/Low ได้ตามวงจรจริง
- ตั้ง Debounce/Filter เฉพาะเมื่อ HAL/Hardware รองรับ
- แสดง Input/Output Live Monitor
- Export ตาราง Wiring สำหรับช่างติดตั้ง

**ข้อจำกัดทางไฟฟ้า:** GUI ไม่สามารถเปลี่ยนวงจร PNP เป็น NPN, Sourcing เป็น Sinking หรือเพิ่มพิกัดกระแส Output ได้ หากบอร์ดไม่รองรับ ให้แสดงเป็น Hardware Capability แบบอ่านอย่างเดียว ไม่ใช่ตัวเลือก Software

### Sequence Options — แสดงตามหน้าที่เกี่ยวข้อง ไม่ใช่หน้าต่างหาก

ผู้ใช้ทั่วไปเลือก Standard Sequence ของ Profile ไม่ต้องสร้าง State Machine เอง

ตั้งค่าได้เฉพาะรายการที่เกี่ยวข้อง เช่น:
- Spindle Stop ก่อนเริ่ม
- ต้องทำ M19 หรือไม่
- ตรวจ Air Pressure หรือไม่
- ตรวจ Tool Present หรือไม่
- ใช้ Pot/Arm/Gripper ตามกลไก
- Timeout ของ Magazine, Arm, Drawbar และ Orientation
- จำนวนครั้ง Retry ที่ปลอดภัยและอนุญาต
- Fault Action และการหยุดเพื่อ Manual Recovery

Advanced Custom Sequence เก็บไว้สำหรับ Integrator ในรุ่นหลัง ไม่ควรเปิดให้ผู้ใช้ทั่วไปแก้ลำดับ Output ได้โดยไม่มีการตรวจ Interlock

### Wizard Page 8 — Review / Validate / Apply

ก่อนบันทึก GUI ต้องแสดง:
- ATC Profile และจำนวน Pocket
- Tool Location Model
- Feedback Method
- M19 Settings
- Logical-to-Physical I/O Mapping
- Resource ที่ถูกใช้และ Resource ที่เหลือ
- รายการ Error/Warning
- Hardware/Firmware Compatibility

ปุ่ม Apply ต้องทำงานตามลำดับ:
1. หยุด/Disable ATC และตรวจ Machine State
2. Validate Configuration
3. สำรอง Configuration เดิม
4. สร้างไฟล์ Configuration/HAL ส่วนที่จำเป็น
5. ตรวจ Syntax และ Resource Conflict
6. Apply หรือแจ้งว่าต้อง Restart LinuxCNC
7. ตรวจสถานะหลังโหลด
8. เปิด ATC เมื่อผ่าน Required Checks เท่านั้น

ต้องมี Rollback หาก Apply ไม่สำเร็จ

## 5. Calibration Wizard

Calibration แยกจาก Setup เพื่อให้ตั้งค่า Hardware ก่อน แล้วค่อยสอนตำแหน่งจริง:

1. ตรวจ I/O และ Sensor ก่อนเคลื่อนที่
2. Jog/สั่ง Home ใน Maintenance Mode
3. ยืนยัน Home และทิศทาง
4. Teach Pocket อ้างอิง
5. ตั้ง Offset, Pitch หรือ Encoder Scale ตามกลไก
6. ตรวจตำแหน่ง Pocket หลายช่อง
7. ทดสอบ Approach Direction และ Repeatability
8. Save Calibration พร้อมวันที่, Profile Version และ Hardware/Firmware Identity

ห้ามใช้ Step Count เป็นหลักฐานตำแหน่งจริง หากระบบไม่มี Feedback และต้องแจ้งผู้ใช้ว่าเป็น Open-loop Positioning

## 6. Overview และ Diagnostics

### Overview

แสดง:
- Current Tool / Requested Tool
- Current Pocket / Target Pocket
- Magazine Position
- ATC State และ Progress
- Spindle Stopped / Oriented
- Drawbar Clamp State
- Air Pressure และ Drive Ready
- Fault/Warning ล่าสุด

### I/O Monitor

แยก Input, Output, Encoder และ Drive Status:
- สี/สถานะ ON/OFF
- Logical Signal Name
- Physical Channel
- Polarity
- Live Value
- แสดง Simulated หรือ Live Hardware ให้ชัดเจน

Output Test ต้องใช้ Maintenance Mode, ตรวจ Machine State และ Interlock ก่อนเสมอ

### Recovery

แสดง:
- State ล่าสุดก่อน Fault
- Sensor ที่ยืนยันแล้ว/ยังไม่ยืนยัน
- Tool อยู่ใน Spindle, Arm หรือ Pocket (Known/Unknown)
- สาเหตุที่ไม่อนุญาตให้ Resume
- ขั้นตอน Manual Recovery และ Operator Confirmation

ห้าม Resume จาก State ที่ไม่ทราบตำแหน่งทูลโดยอัตโนมัติ

## 7. ตัวอย่าง User Journey

**ตัวอย่าง: Umbrella 16 Pocket + Home/Index + Pot Up/Down**

1. เปิด Tab ATC
2. เลือก Hardware 7i92 + 1x 7i76
3. เลือก Umbrella
4. ใส่จำนวน Pocket = 16
5. เลือก Fixed Pocket
6. เลือก Home + Index
7. เลือก Pot Up/Down
8. เลือก M19 ตามความต้องการของเครื่อง
9. ตรวจรายการ Logical Signal ที่ระบบสร้าง
10. Map DI/DO จากช่องที่มีจริง
11. กด Validate
12. ทำ Calibration และทดสอบ Pocket
13. Save และ Enable ATC

ผู้ใช้ไม่ต้องเปิดแก้ HAL/INI และไม่ต้องพิมพ์ชื่อ Pin เอง

## 8. สิ่งที่ไม่ทำใน GUI รุ่นแรก

- Matrix/Shelf Warehouse และ Robot
- Multi-Magazine Coordination
- Turret/Lathe ATC
- Custom PLC Programming
- Visual Sequence Editor แบบลากวาง
- การเปลี่ยน FPGA Firmware จาก GUI
- การตั้งค่า Electrical Capability ที่ PCB ไม่มี
- การรับรอง Safety ผ่าน Software

## 9. เกณฑ์ตรวจรับ GUI Prototype

- [ ] เลือก 5 ATC Type ได้
- [ ] Wizard ซ่อน/แสดงค่าตามกลไก
- [ ] สร้าง Required/Optional Logical Signal อัตโนมัติ
- [ ] เลือกได้เฉพาะ Physical Resource ที่ Hardware Manifest อนุญาต
- [ ] ตรวจ Mapping ซ้ำและ Resource ขาด
- [ ] ตั้ง M19 และ Timeout ได้ตาม Interface
- [ ] Save/Load Configuration ได้
- [ ] Validate ก่อน Apply
- [ ] Backup/Rollback ได้
- [ ] แสดง Live I/O และ Simulation แยกกัน
- [ ] ปิด GUI แล้ว ATC Runtime ไม่หยุดกลาง Sequence
- [ ] ผู้ใช้ทั่วไปไม่ต้องแก้ HAL/INI ด้วยตนเอง

## 10. หมายเหตุด้านสถานะ

เอกสารนี้เป็น UX/Workflow Specification สำหรับเริ่มทำหน้าจอและ Data Model ยังไม่ใช่ GUI ที่ Implemented แล้ว และยังไม่ยืนยัน Hardware Capability ของ 7i92 + 7i76 หรือ 7i76 สองชุดจนกว่าจะตรวจ HostMot2/Bitfile/SmartSerial จริง


## ขั้นตอนที่ 7 — การกำหนด I/O และการจัดสรรอัตโนมัติ

รายละเอียดการตรวจ Hardware Manifest, Resource Reservation, Auto-map, Manual Override, ความเข้ากันได้ทางไฟฟ้า และ Diagnostics อยู่ใน [Configuration Engine V1](../docs/CONFIGURATION-ENGINE-V1.md) และ [รูปแบบไฟล์ Configuration](04-CONFIGURATION-FORMAT.md)


## หน้า Wizard 8 — ตรวจทาน / ตรวจสอบ / สร้าง Candidate

ขั้นตอนสุดท้ายต้องแสดง Hardware/Profile Summary, ผล Validation, ระดับความรุนแรงของปัญหา, Apply Transaction, Staging, Diff, Backup/Rollback, Post-load Verification และ Commissioning โดยแยกจากการ Enable ATC อย่างชัดเจน
