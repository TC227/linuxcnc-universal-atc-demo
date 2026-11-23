# 5. Spindle Orientation และ M19

สถานะ: **DRAFT**

## 5.1 วัตถุประสงค์

M19 ใช้สั่งให้ Spindle จัดตำแหน่งไปยังมุมที่กำหนด เป็นคนละหน้าที่กับการหมุน Magazine โดย ATC อาจต้องจัดมุม Spindle ให้ตรงเพื่อให้ Key ของ Tool Holder, แขนเปลี่ยนทูล หรือกลไก Drawbar เข้าตำแหน่งได้

## 5.2 ข้อกำหนดการทำงาน

- มุมเป้าหมาย
- ทิศทางการหมุน: ทางสั้นที่สุด, CW หรือ CCW ตามที่ระบบรองรับ
- Orientation Offset
- Position Tolerance
- Timeout
- Encoder Feedback
- Drive Ready/Fault
- สัญญาณยืนยัน Orientation Complete
- สถานะ Brake/Lock หากเครื่องมี

## 5.3 ทางเลือก Hardware

1. Servo Spindle Drive ที่รองรับ Closed-loop Position Mode
2. VFD ที่มีฟังก์ชัน Spindle Positioning/Orientation และรองรับ Encoder Feedback
3. External Orientation Controller ที่รับมุม/ทิศทางและส่ง Ready/Complete/Fault กลับ
4. ระบบจัดตำแหน่งความเร็วต่ำแบบเดิม เฉพาะกรณีที่พิสูจน์ความทำซ้ำและความปลอดภัยได้

**ข้อสำคัญ:** การต่อ Encoder เข้า LinuxCNC ไม่ได้ทำให้ VFD ทั่วไปสามารถควบคุมตำแหน่งได้เอง Drive ต้องมีความสามารถควบคุมตำแหน่ง หรือทำงานร่วมกับ Controller แบบ Closed-loop

## 5.4 ข้อกำหนด Encoder

- เลือก Differential A/B/Z เมื่อชนิด Encoder และระยะสายต้องการ
- ระบุให้ชัดว่า PPR/CPR ใช้ความหมายแบบใด และนับ x1/x2/x4
- ระบุอัตราทดระหว่าง Spindle กับ Encoder
- กำหนดทิศทางและวิธีใช้ Index
- ตรวจ Zero Offset และการวนรอบมุม 0–360 องศา
- แยกทรัพยากร Spindle Encoder ออกจาก Encoder ของแกน CNC และ Magazine

## 5.5 Brake และ Lock

Brake อาจใช้ยึด Spindle หลังจัดตำแหน่ง แต่ไม่ควรใช้แทน Closed-loop Positioning เว้นแต่กลไกถูกออกแบบมารองรับโดยตรง หากมี Feedback ให้แยกสัญญาณ Brake Command และ Brake Confirm

## 5.6 การเชื่อมต่อ LinuxCNC

ใช้ Spindle Orient/M19 Interface ที่ LinuxCNC รุ่นเป้าหมายรองรับ ต้องตรวจชื่อ HAL Pin, Handshake และความหมายของ P/Q/R จากเอกสารหรือ Source ของ LinuxCNC รุ่นที่ติดตั้งจริงก่อนพัฒนา ห้ามนำชื่อ Pin จากตัวอย่างที่ยังไม่ตรวจสอบมาใช้เป็นข้อกำหนด PCB

## 5.7 Interlock ก่อนแขนเข้าจับทูล

- ยืนยัน Spindle หยุดหมุน
- ยืนยัน Orientation Complete
- Drive ไม่มี Fault
- Brake/Lock อยู่สถานะที่เครื่องต้องการ
- แกนเครื่องและ Magazine อยู่ตำแหน่งแลกทูลที่ปลอดภัย

หาก Orientation Timeout หรือ Encoder ไม่สอดคล้อง ต้องหยุด ATC Sequence และเข้าสู่ Fault/Recovery


## 5.8 GUI Configurator และ Servo Native Orientation

ข้อกำหนดหน้าจอ Wizard หน้า 6 ซึ่งใช้ LinuxCNC M19 เป็นคำสั่งมาตรฐาน และรองรับ LinuxCNC Encoder/PID, Servo Drive Native Orientation และ External Orientation Controller อยู่ใน [Spindle Orientation / M19 Configurator Screen V1](../software/10-SPINDLE-ORIENTATION-M19-SCREEN-V1.md)
