# ขอบเขตการเผยแพร่ Public Demo

## วัตถุประสงค์

Repository นี้เป็นชุดตัวอย่างสาธารณะของ LinuxCNC Universal ATC Configurator และ VMC850 Simulation จัดทำขึ้นเพื่อให้ตรวจสอบแนวคิด ทดลอง GUI เรียนรู้ และทดสอบซอฟต์แวร์ โดยแยกออกจาก Repository พัฒนาหลัก

## ที่มาของ Source Snapshot

- Repository ต้นทาง: `linuxcnc-universal-atc`
- Branch ต้นทาง: `feature/vmc850-atc-simulation`
- Commit ต้นทาง: `13ea6540dc76942694cbad45f58e74392a62954e`
- วันที่ส่งออก: 23 พฤศจิกายน 2026

คัดลอกเฉพาะไฟล์ Source และเอกสารที่จำเป็นสำหรับ Demo โดย Repository นี้มี Git History แยกเป็นของตนเอง

## ไฟล์และเนื้อหาที่รวมไว้

- Python Configurator, Validation Engine, Simulation Runtime และ Tests
- QtVCP Panel Integration
- ATC Profile ทั่วไปและ JSON Schema
- Hardware Manifest สำหรับ Simulation และตัวอย่าง Configuration
- VMC850 Vismach Model แบบ Schematic พร้อมคำแนะนำการติดตั้ง
- เอกสารอธิบายกลไก ATC และสถาปัตยกรรม Software

## สิ่งที่ไม่นำมาเผยแพร่

- Git Commit History, Branch สำหรับพัฒนา, Pull Request และการสนทนาใน Issue ภายใน
- PCB Schematic, Board Layout, รายการอุปกรณ์, Pin Map และเอกสารจัดสรรทรัพยากร Hardware
- Hardware Manifest ของบอร์ด Clone 7i92/7i76 ที่ยังไม่ได้ยืนยัน
- Machine Configuration เฉพาะเครื่อง, Network Address, Credential และ Personal Path
- Roadmap ภายในและบันทึกโครงการอื่นที่ไม่เกี่ยวข้อง

## ขอบเขตด้านความปลอดภัย

Hardware Manifest ที่รวมไว้ระบุสถานะเป็น `simulated` อย่างชัดเจน ห้ามนำไปตีความว่าเป็น Hardware Definition ที่ผ่านการตรวจสอบแล้ว

ATC Enable และ Live Apply ยังคงปิดอยู่ การสร้าง Candidate มีไว้สำหรับ LinuxCNC Simulation ที่แยกจาก Machine Configuration จริงเท่านั้น

Demo นี้ไม่เหมาะสำหรับควบคุมเครื่องจักรจริงหรือใช้ในงานที่มีความเสี่ยงด้านความปลอดภัย

## License

ขณะนี้ยังไม่ได้เลือกหรือเพิ่ม License ให้ Repository นี้ การเปิด Repository เป็น Public ไม่ได้ให้สิทธิ์ในการนำ Source Code ไปใช้ แก้ไข หรือแจกจ่ายต่อโดยอัตโนมัติ
