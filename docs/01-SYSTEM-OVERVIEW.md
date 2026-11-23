# 1. ภาพรวมระบบ Universal ATC

สถานะ: **DRAFT**

## 1.1 แนวคิดผลิตภัณฑ์

พัฒนาแพลตฟอร์มควบคุม ATC สำหรับ LinuxCNC โดยรองรับความหลากหลายของเครื่องผ่านการประกอบ Configuration จากหลายคุณสมบัติ แทนการเขียนโปรแกรมแยกตามชื่อ Magazine แบบตายตัว

## 1.2 แยกการออกแบบเป็น 5 มิติ

| มิติ | ตัวเลือกตัวอย่าง |
|---|---|
| รูปแบบการจัดเก็บ | Umbrella, Disc/Drum, Chain, Linear Rack, Matrix/Shelf, Turret, Central Storage |
| วิธีขับเคลื่อน | DC Gearmotor, Stepper, Servo, Pneumatic/Hydraulic Index, External PLC |
| กลไกส่งทูล | Direct/Pot Movement, Single Arm, Double Arm, Swing Arm, Robot/Gantry |
| Feedback ตำแหน่ง | Home/Index, Sensor ต่อ Pocket, Binary/BCD/Gray Code, Incremental/Absolute Encoder |
| รูปแบบจัดการทูล | Fixed Pocket หรือ Random Pocket |

ตัวอย่าง: Chain + Servo + Double Arm + Incremental Encoder + Random Pocket เป็นการประกอบคุณสมบัติจากทั้ง 5 มิติ

## 1.3 ชั้นการทำงานของระบบ

1. **Machine Electrical:** Sensor 24V, Solenoid Valve, Motor Drive, Brake และ Safety Circuit
2. **Mesa/HostMot2:** Physical I/O, Stepgen, Encoder และ SmartSerial ตาม Firmware จริง
3. **HAL Abstraction:** Map Physical Pin เป็น Logical ATC Signal
4. **ATC Manager:** Sequence, State, Timeout, Fault และ Recovery
5. **LinuxCNC Integration:** M6, Tool Prepare/Change Handshake, Tool Table และ Spindle Orientation
6. **QtVCP GUI:** Setup, Mapping, Calibration, Diagnostics และ Recovery Guidance

## 1.4 การแบ่งหน้าที่

- FPGA/HostMot2 ไม่ควรบรรจุ Sequence เฉพาะเครื่องทุกแบบ
- GUI ไม่ควรเป็นตัวควบคุม Output หลักระหว่าง Automatic Cycle
- ATC Manager ไม่ใช่ Safety-rated Controller
- E-stop, Guard, STO และการป้องกันการเคลื่อนที่อันตรายต้องใช้ Hardware Safety ที่เหมาะสม
- ต้องกำหนดให้ชัดว่า LinuxCNC Tool Table หรือ ATC Location Manager เป็นแหล่งข้อมูลหลักของ Tool/Pocket เพื่อไม่ให้ข้อมูลขัดแย้งกัน

## 1.5 เป้าหมายการออกแบบ

- ผู้ใช้เลือก Profile และกำหนด I/O Mapping ผ่าน GUI
- ตรวจ Configuration ก่อน Apply
- ใช้ Sequence Building Blocks ซ้ำได้
- มี Manual Diagnostics และ Guided Recovery
- รองรับ Remote I/O หรือ External PLC เมื่อทรัพยากรบอร์ดหลักไม่พอ
- ทุก Output ต้องกำหนด Safe State และเงื่อนไขการทำงาน

## 1.6 สิ่งที่ยังไม่รวมในรุ่นแรก

- การรับรอง Safety ของเครื่องจักร
- การรับประกันว่าสายไฟชุดเดียวใช้ได้กับทุกยี่ห้อโดยไม่ตรวจวงจร
- Robot Motion Planning เต็มรูปแบบ
- RFID Protocol เฉพาะผู้ผลิต
- การรับประกันว่า VFD ทุกตัวรองรับ M19

## 1.7 ประเด็นที่ต้องยืนยัน

- รุ่น Schematic/PCB ของ 7i92 และ 7i76 ที่จะใช้
- FPGA, HostMot2 Bitfile และ SmartSerial Firmware
- จำนวน Encoder สำหรับ Spindle, Magazine และกลไกเสริม
- จำนวน DI/DO และกระแส Output ต่อช่อง
- รองรับ LinuxCNC 2.9 เท่านั้น หรือเผื่อรุ่นถัดไป
