# VMC850 simulation: QtDragon, Vismach and ATC Monitor

สถานะ ณ 17 พฤศจิกายน 2026: สร้างและเปิดบน Raspberry Pi 4 ที่มี LinuxCNC/QtVCP แล้ว
รองรับการทดลองผ่าน Desktop หรือ VNC โดยใช้ QtDragon รุ่นปกติ ไม่ใช่ QtDragon HD

## สิ่งที่มีในรุ่นนี้

- Visual configurator พร้อมภาพและคำอธิบาย Sensor/Output, Auto-map, Validate และ Apply
- จานแนวนอน Umbrella/Carousel 12 ช่อง ขับ DC แบบ CW/CCW ใช้ Home + Index proximity
- Magazine เข้า/ถอยด้วยกระบอกลม ประตู ATC และ Drawbar พร้อม feedback จำลอง
- Fixed pocket inventory: ทูลอยู่ในสปินเดิลหนึ่งด้าม ช่องประจำจึงว่างหนึ่งช่อง
- Vismach รูปทรงต้นฉบับจาก Python primitives: โต๊ะ X/Y, หัว Z, จาน, ก้ามรองทูล,
  ประตู, Drawbar, เขี้ยวขับสปินเดิล และมาร์ก M19
- ATC Monitor: ลำดับ, Input/Output, Resource ID, ON/OFF, สัญญาณที่รอและ Timeout
- จำลอง Sensor เสียได้ และตั้ง Sensor เป็นไม่ใช้ในหน้าคอนฟิกได้
- M19 จำลอง: หมุนหามุมเป้าหมาย แสดงองศา และยืนยันเมื่อถึงมุมและนิ่งแล้ว

## สร้างคอนฟิกใหม่

ใช้ Linux ที่ติดตั้ง LinuxCNC, QtVCP, Vismach, PyQt5, PyOpenGL และ jsonschema แล้ว
Virtual environment ต้องมองเห็นแพ็กเกจ LinuxCNC ของระบบ:

```bash
python3 -m venv --system-site-packages .venv-test
.venv-test/bin/python -m pip install -e '.[test]'
.venv-test/bin/python scripts/build_vmc850_sim.py
```

สคริปต์จะคัดลอก QtDragon metric sample ที่ติดตั้งอยู่มาสร้าง base แยก
และพิมพ์ path ของ Candidate ที่สร้างใหม่ เช่น:

```text
~/linuxcnc/configs/universal-atc-generated/vmc850-12-tool-sim-r001
```

ถ้ามีชื่อดังกล่าวแล้ว จะสร้าง suffix ใหม่โดยไม่เขียนทับ
หากตำแหน่ง sample ต่างออกไป ใช้ `--sample-dir /path/to/qtdragon_xyz`
หรือใช้ `--base-config-dir /path/to/isolated-sim` ซึ่งต้องมี `axis.ini`
และสัญญาณ HAL `Xpos`, `Ypos`, `Zpos` แบบเดียวกับ QtDragon sample

เปิดจาก Linux Desktop/VNC Terminal โดยใช้ path ที่สคริปต์รายงาน:

```bash
linuxcnc ~/linuxcnc/configs/universal-atc-generated/vmc850-12-tool-sim-r001/axis.ini
```

ต้องมี DISPLAY ที่ใช้งานจริงสำหรับหน้าต่าง QtDragon และ Vismach
ส่วน `QT_QPA_PLATFORM=offscreen` ใช้เฉพาะ automated tests

## ทดลองใช้งาน

1. เข้า ATC ใน QtDragon; ปุ่ม ATC Monitor / I/O ใช้เปิดหน้าต่าง Monitor
2. เลือก T4 แล้วกดเปลี่ยนทูล ดูขั้นตอนและไฟ Input/Output ไปพร้อมกับ Vismach
3. เปลี่ยนเป็น T9: คืน T4 ก่อนรับ T9; ในจานเหลือ 11 ด้ามและ Pocket 9 ว่าง
4. กดหมุน Spindle SIM +90° แล้วกด M19 SIM เพื่อดูการกลับเข้าจุดอ้างอิง
5. มาร์กสีส้มและเขี้ยวหมุนตามสปินเดิล มาร์กสีแดงอยู่ที่มุมเป้าหมาย
6. IN POSITION ต้องขึ้นหลังถึงมุม; ลองจำลอง SPINDLE_ORIENT_IN_POSITION เสียเพื่อดู Timeout
7. ลอง DRAWBAR_UNCLAMPED เสีย: ลำดับต้องหยุดและปิดคำสั่ง Output เมื่อ Timeout
8. หลัง Stop/Fault ใช้ Reset SIM เพื่อเริ่มใหม่; Reset คืน inventory จำลองทั้งหมด

## ไฟล์ที่สร้าง

| ไฟล์ | หน้าที่ |
|---|---|
| `axis.ini` | QtDragon simulation พร้อมพารามิเตอร์ ATC |
| `atc_config.json` | คอนฟิกและ Mapping ที่ Apply |
| `atc_validation.json` | ผล Validate |
| `atc_io_map.csv` | Logical signal → Simulator resource |
| `atc_apply_manifest.json` | รายการไฟล์และสถานะ Candidate |
| `atc_generated.hal` | โหลด Vismach สำหรับซิมที่รองรับ |
| `atc_vismach.hal` | เชื่อม XYZ จำลองเข้ากับภาพ 3D |
| `vismach_vmc/vmcgui` | โมเดล Vismach |
| `scripts/vmc850_vismach.py` | ต้นฉบับโมเดลสำหรับ Apply ซ้ำ |
| `src/atc_configurator/` | Configurator, simulation controller และ Monitor |

## ขอบเขตและงานต่อ

Runtime นี้เป็นตัวสาธิตที่ขับด้วย Qt timer; Feedback และ M19 เป็นการจำลอง
ยังไม่ได้ผูกคำสั่ง M6/M19 จาก interpreter เข้ากับลำดับ ATC
แกน XYZ หลักอ่านจาก LinuxCNC simulation แต่ระยะยกหัวสำหรับ ATC เป็น animation offset
จึงไม่ใช่คำสั่งเคลื่อน Joint Z จริง และยังไม่มีการตรวจการชน
การเก็บทูลเป็น fixed pocket 12 ช่องและ Reset คืนค่าเริ่มต้น ไม่มี recovery หลังไฟดับ
การข้าม Sensor ใช้สำหรับสำรวจคอนฟิก/ซิม ไม่ใช่การรับรอง interlock เครื่องจริง

ยังไม่รองรับการปลดทูลด้วย Z กดกระเดื่องแบบเฉพาะรุ่น, normal/ATC travel envelope,
ตำแหน่ง Z หลายระดับที่สอนค่าได้ หรือการเปลี่ยนขอบเขตเดินระหว่างโหมด
รายละเอียดแนวทางอยู่ใน [แผนพัฒนา Z สำหรับ ATC](Z-ATC-POSITIONS.md)

## ตรวจสอบ Source

```bash
bash scripts/test_ubuntu_local.sh
```

ตรวจ inventory กับ HAL ที่กำลังเปิดอยู่บน Desktop ได้ด้วย
`scripts/check_vmc_inventory.py` โดยสคริปต์นี้สั่งสถานะ SIM เพื่อทดสอบจริง
ควรรันเมื่อไม่ได้กำลังทดลองด้วยมือ

โมเดลใน `scripts/vmc850_vismach.py` สร้างขึ้นในโปรเจกต์นี้จาก primitives
ไม่ได้รวม STL ของผู้ผลิตหรือโมเดลจาก GrabCAD
ดู [เอกสาร Vismach ของ LinuxCNC](https://www.linuxcnc.org/docs/stable/html/gui/vismach.html)
สำหรับวิธีเปลี่ยนรูปทรงและนำเข้า STL/OBJ
