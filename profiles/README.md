# รายการ ATC Profile

สถานะ: **DRAFT — V1 Scope จำกัด 5 รูปแบบทั่วไป**

## หลักการ

Profile คือชุดค่าเริ่มต้นของกลไกและ Sequence ไม่ใช่การผูกชื่อยี่ห้อเครื่อง Profile ต้องประกอบจาก:
- Magazine Geometry
- Indexing Drive
- Position Feedback
- Transfer Mechanism
- Tool Location Model
- Required/Optional Logical Signals

Magazine และ Transfer Mechanism เป็นคนละมิติ เช่น Rotary Disc อาจใช้ Direct Pickup หรือ Double Arm ได้

## V1 — รูปแบบที่ทำ GUI ก่อน

| ID | Magazine | Transfer เริ่มต้น | หมายเหตุ |
|---|---|---|---|
| ATC-01 | Umbrella / Parasol | Direct หรือ Pot Movement | เริ่มจาก Fixed Pocket |
| ATC-02 | Rotary Disc / Carousel | Direct Pickup | รองรับ Home/Index หรือ Code/Encoder |
| ATC-03 | Side-mounted | Double Arm 180° | แยก Sensor ของ Arm/Gripper |
| ATC-04 | Chain Magazine | Double Arm 180° | รองรับ Servo/Encoder เมื่อ Hardware มี |
| ATC-05 | Linear Rack | Direct Pickup | ใช้ Home/Limit และ Pitch/Position |

## Future Extension

| ID | รูปแบบ | สถานะ |
|---|---|---|
| FUT-01 | Turret | ยังไม่อยู่ใน GUI V1 |
| FUT-02 | Matrix / Shelf | ยังไม่อยู่ใน GUI V1 |
| FUT-03 | Multi-Magazine / Robot Warehouse | ยังไม่อยู่ใน GUI V1 |

## Profile Manifest

แต่ละ Profile ต้องระบุ:
- Stable Profile ID และ Version
- Parameter Schema และค่าเริ่มต้น
- Required / Optional / Conditional Logical Signal
- Position Feedback ที่รองรับ
- Transfer Mechanism ที่รองรับ
- Sequence Definition และ Timeout
- Fault/Recovery Matrix
- Calibration Procedure
- Simulation Test Cases
- Hardware Capability Requirement

Profile ที่ต้องใช้ Encoder หรือ Stepgen จะเปิดให้เลือกได้ต่อเมื่อ Hardware Manifest ยืนยัน Resource จริง

ใช้ชื่อกลาง เช่น `umbrella-pot-v1` แทนชื่อผู้ผลิต เว้นแต่เป็น Vendor-specific Profile โดยตั้งใจ

Profile คงสถานะ DRAFT จนกว่าจะทดสอบกับเครื่องที่ระบุรุ่น, Wiring, LinuxCNC Version และ HostMot2 Firmware พร้อมหลักฐาน
