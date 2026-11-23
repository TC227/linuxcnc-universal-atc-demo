# Configuration Engine V1 — ขอบเขตและวิธีใช้งาน

สถานะ: **AXIS QtVCP Panel + Safe Candidate Generator Implemented — Pi 4 Validation Pending**
Branch: `feature/configuration-engine-v1`

## เป้าหมายของ Milestone แรก

สร้างแกนกลางที่ไม่ขึ้นกับ GUI เพื่อให้ QtVCP ทั้ง 8 หน้าอ่านและเขียน Configuration รูปแบบเดียวกัน:
- JSON Schema ตรวจโครงสร้างข้อมูล
- Profile Catalog สร้าง Logical Signal ตาม ATC Type
- Hardware Capability Manifest อธิบาย Resource ที่มีจริง
- Auto Mapper จัดสรร DI/DO โดยไม่ใช้ Resource ซ้ำ
- Validation Engine ตรวจ Profile, Feedback, Transfer, I/O, Encoder, Stepgen, Communication และ M19
- Validation Report ส่งกลับให้ GUI แสดง Error/Warning และปุ่มกลับไปหน้าที่แก้ไข

## สถานะ Hardware ที่ต้องเข้าใจ

ตัวอย่าง Manifest ใน `examples/hardware-manifests/simulator-24di-16do.json` เป็น **Simulator เท่านั้น** ไม่ใช่ 7i92/7i76 Pinout และไม่ใช่การยืนยันจำนวน I/O ของบอร์ดจริง

Manifest ของ 7i92 + 7i76 Clone จะสร้างได้เมื่อมีหลักฐาน Board Revision, Schematic, HostMot2 Bitfile/Hash, HAL Pin และ Connector Mapping ครบ การใช้ Manifest สถานะ `unverified` จะทำให้ Validation อนุญาต Preview/Save Draft แต่ Block Live Apply

## โครงสร้างหลัก

- `schemas/atc-config.schema.json` — สัญญาข้อมูล Configuration
- `schemas/hardware-manifest.schema.json` — สัญญาข้อมูล Hardware
- `schemas/validation-report.schema.json` — สัญญาผล Validation
- `profiles/v1/catalog.json` — Profile ทั่วไป 5 รูปแบบ
- `src/atc_configurator/profiles.py` — ขยาย Logical Signal ตาม Profile/Pocket/Feedback
- `src/atc_configurator/io_mapper.py` — Auto-map แบบ deterministic
- `src/atc_configurator/validator.py` — Validation แบบ Offline
- `src/atc_configurator/cli.py` — คำสั่งตรวจ Configuration
- `src/atc_configurator/wizard_model.py` — Shared Model ของ Wizard ทั้ง 8 หน้า
- `src/atc_configurator/gui.py` — PyQt5 Wizard 8 หน้าและ Candidate Apply UI
- `src/atc_configurator/generator.py` — สร้างสำเนา Axis Simulation พร้อม ATC INI/JSON/CSV และ HAL stub
- `qtvcp/panels/universal_atc/` — QtVCP Panel UI/Handler สำหรับฝังใน AXIS
- `scripts/install_pi4_axis_test.sh` — ติดตั้งโฟลเดอร์ทดสอบบน Pi 4 โดยไม่แก้ Machine Config เดิม
- `tests/` — Unit Tests

## ติดตั้งและทดสอบ

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest
```

## ทดลองตรวจตัวอย่าง

ตัวอย่าง Configuration ตั้งใจเริ่มจาก Mapping ว่าง เพื่อให้เห็น Required Signal ที่ขาด:

```bash
atc-config validate \
  --config examples/configurations/chain-24-double-arm.json \
  --manifest examples/hardware-manifests/simulator-24di-16do.json
```

ผลจะรายงาน Missing Required I/O และ Hardware Not Verified เพราะเป็น Simulation Manifest ไม่อนุญาต Live Apply

## ทดลองเปิด GUI Prototype

สำหรับการเปิด Wizard แบบ Standalone บน Debian/LinuxCNC ที่มี PyQt5:

    sudo apt install python3-pyqt5
    python3 -m venv --system-site-packages .venv
    . .venv/bin/activate
    python -m pip install -e ".[test]"
    atc-config-gui --data-dir .

หากรันจาก Source Tree โดยไม่ติดตั้ง Entry Point:

    python -m atc_configurator.gui --data-dir .

เริ่มต้นด้วย Simulator Manifest เพื่อทดลอง Wizard โดยไม่ต่อ Hardware. สามารถเลือก 7i92 + 7i76 Unverified Template เพื่อดูสถานะ Resource ที่ยังไม่มีหลักฐานได้ แต่ไม่มี Pin ใดถูกเสนอเป็น Available.

## AXIS QtVCP Integration และ Apply Candidate

ติดตั้ง QtVCP Panel ลง AXIS ผ่าน X11 embedding ตามคู่มือใน qtvcp/README.md. บน Pi 4 ให้รัน:

    bash scripts/install_pi4_axis_test.sh

สคริปต์สร้างโฟลเดอร์ใหม่ ~/linuxcnc/configs/universal-atc-axis-test จาก Stock AXIS Simulation Config เท่านั้น ไม่แตะ Machine Config เดิมหรือคอนฟิกเครื่องจริง

เมื่อกด Apply → Generate Test Config:
- สร้างสำเนา Axis Simulation Config ลงโฟลเดอร์ generated/<config-id>-rNNN
- เพิ่ม [ATC] section ลง axis.ini พร้อมค่าที่เลือกจาก Wizard
- บันทึก atc_config.json, atc_validation.json, atc_io_map.csv และ atc_apply_manifest.json
- เพิ่ม POSTGUI_HALFILE ชื่อ atc_generated.hal ซึ่งมี comment เท่านั้น
- คัดลอก QtVCP Panel, Configurator Source, Profile, Schema และ Manifest ไปพร้อมกัน
- ไม่แก้ไข Source axis.ini, ไม่แก้ Machine Config เดิม และไม่สั่ง Hardware

## ขอบเขตที่ยังไม่ทำ

- ยังไม่มี ATC Runtime Component ที่อ่าน [ATC] values
- ยังไม่มี active HAL net หรือการสร้าง Physical I/O wiring
- ยังไม่เชื่อม LinuxCNC HAL Status/Action, ไม่สั่ง Physical Output/Motion และไม่สั่ง M6/M19
- Apply นี้เป็น Candidate Generation ไม่ใช่ Live Apply/Reload/Restart
- 7i92 + 7i76 Clone ยังคง UNVERIFIED; ไม่มี Pin Mapping ที่เดาขึ้นมา
- ยังไม่รับรอง Safety Function

อัปเดต 17 พฤศจิกายน 2026: เปิด QtDragon บน Pi 4 พร้อม Visual ATC,
Vismach VMC850 และ Monitor แล้ว ดู [คู่มือซิม](VMC850-SIMULATION.md)
ข้อจำกัด Runtime ด้านบนหมายถึง Production Runtime; รุ่นซิมมี Qt-timer controller
และเชื่อมเฉพาะ HAL สำหรับภาพจำลอง ไม่ได้สั่ง M6/M19 หรือ Hardware จริง
Candidate ของ QtDragon 12-tool ที่รองรับจะโหลด `atc_vismach.hal` เพิ่ม
จึงไม่ใช่ comment-only HAL ตามต้นแบบ AXIS ดั้งเดิม
