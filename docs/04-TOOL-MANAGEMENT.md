# 4. การจัดการ Tool และ Pocket

สถานะ: **DRAFT**

## 4.1 แยก Tool Number ออกจาก Pocket Number

- **Tool Number (T):** หมายเลขทูลที่โปรแกรม G-code เรียกใช้
- **Pocket Number (P):** ตำแหน่งช่องเก็บทูลจริงใน Magazine
- **Spindle Tool:** ทูลที่ติดตั้งอยู่ใน Spindle
- **Transfer Location:** ตำแหน่งชั่วคราวระหว่างอยู่ใน Gripper หรือแขนเปลี่ยนทูล

ห้ามสมมติว่า T เท่ากับ P เสมอไป

ตัวอย่าง:

| Tool | Pocket |
|---:|---:|
| T1 | P12 |
| T2 | P3 |
| T3 | P18 |
| T4 | P7 |

## 4.2 Fixed Pocket และ Random Pocket

**Fixed Pocket:** ทูลหนึ่งหมายเลขมีช่องประจำตัว เมื่อนำทูลกลับจะกลับไปช่องเดิมตามตาราง

**Random Pocket:** ทูลสามารถย้ายไปอยู่ช่องอื่นหลังการเปลี่ยนทูล ระบบต้องปรับข้อมูล Tool-to-Pocket หลังจากตรวจสอบการแลกทูลทางกายภาพสำเร็จแล้ว

ควรใช้ LinuxCNC Tool Table และ Tool Change Handshake ตามกลไกที่ LinuxCNC รุ่นเป้าหมายรองรับ ต้องตรวจชื่อ HAL Pin และความหมายจากเอกสาร/Source รุ่นจริงก่อนพัฒนา ไม่ควรสร้างฐานข้อมูล Tool ซ้ำอีกชุดโดยไม่มีการกำหนดแหล่งข้อมูลหลัก

## 4.3 การเปลี่ยนทูลแบบ Transaction

1. รับ Tool ที่ต้องการและค้นหา Source/Destination Pocket
2. ตรวจ Mapping และสถานะช่องว่าง/ช่องที่มีทูล
3. เคลื่อน Magazine ไปสถานีแลกทูล
4. ทำกลไกแลกทูล
5. ตรวจ Tool ใน Spindle และตำแหน่งทูลที่นำกลับ
6. Commit การเปลี่ยน Tool/Pocket หลังตรวจสอบทางกายภาพแล้วเท่านั้น
7. แจ้ง LinuxCNC ว่าการเปลี่ยนทูลเสร็จสมบูรณ์

หากเกิด Fault ก่อน Commit ให้รักษาสถานะล่าสุดที่ยืนยันได้และเข้าสู่ Recovery ห้ามเปลี่ยน Tool Table เพียงเพราะมีการสั่ง Output แล้ว

## 4.4 สถานะ Occupancy

แต่ละ Pocket และตำแหน่งชั่วคราวควรรองรับสถานะ:
- UNKNOWN — ยังไม่ทราบ
- EMPTY — ว่าง
- OCCUPIED(tool_id) — มีทูล
- RESERVED — จองช่องแล้ว
- IN_TRANSFER — กำลังเคลื่อนย้ายทูล

## 4.5 วิธีระบุตัวตนทูล

- Tool Table ที่ผู้ปฏิบัติงานดูแล
- Pocket Occupancy Sensor
- Tool Presence Sensor
- RFID/Barcode/Encoded Tool Holder (ทางเลือก)
- ระบบวัดความยาวและเส้นผ่านศูนย์กลางทูล (เป็นระบบแยก)

การตรวจพบว่ามีทูลอยู่ ไม่ได้หมายความว่าระบบทราบว่าเป็น Tool Number ใด
