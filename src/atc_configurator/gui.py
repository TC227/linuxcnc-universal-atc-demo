"""PyQt5 eight-page ATC setup wizard with isolated Axis candidate generation.

The Apply action only copies a stock Axis simulation config and writes ATC
metadata into that copy. It never edits the source machine config, creates
active physical HAL nets, drives outputs or commands motion.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
        QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
        QMainWindow, QMessageBox, QPushButton, QScrollArea, QSpinBox,
        QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
        QHeaderView, QListWidget,
    )
except ImportError as exc:  # pragma: no cover - depends on LinuxCNC desktop image
    _QT_IMPORT_ERROR = exc
else:
    _QT_IMPORT_ERROR = None

from .wizard_model import WizardModel
from .generator import generate_candidate


PAGE_TITLES = [
    "1  ฮาร์ดแวร์",
    "2  ประเภท ATC",
    "3  Magazine",
    "4  กลไกส่งทูล",
    "5  ระบบ Feedback",
    "6  จัดแนว Spindle (M19)",
    "7  กำหนด I/O",
    "8  ตรวจทาน",
]

PROFILE_LABELS = {
    "umbrella-parasol-v1": "แมกกาซีนแบบร่ม (Umbrella / Parasol)",
    "rotary-disc-v1": "จานหมุน (Rotary Disc / Carousel)",
    "side-mounted-double-arm-v1": "แมกกาซีนด้านข้าง (Side-mounted)",
    "chain-double-arm-v1": "แมกกาซีนแบบโซ่ (Chain)",
    "linear-rack-v1": "รางเก็บทูล (Linear Rack)",
}

TRANSFER_LABELS = {
    "direct_pickup": "สปินเดิลรับทูลโดยตรง (Direct Pickup)",
    "pot_movement": "รับทูลโดยตรง + Pot เคลื่อนที่",
    "single_arm": "แขนเดี่ยว / กริปเปอร์เดี่ยว",
    "double_arm_180": "แขนคู่ / แลกทูล 180°",
}

FEEDBACK_LABELS = {
    "per_pocket": "เซ็นเซอร์แยกทุก Pocket",
    "gray_code": "รหัส Gray Code",
    "binary_code": "รหัส Binary",
    "bcd": "BCD",
    "home_index": "Home + Index",
    "incremental_encoder": "Encoder แบบ Incremental",
    "absolute_encoder": "Encoder แบบ Absolute",
    "drive_in_position": "สัญญาณ Drive In-position",
    "open_loop_step_count": "นับ Step แบบ Open-loop (มีข้อจำกัด)",
}

BACKEND_LABELS = {
    "linuxcnc_encoder_pid": "Encoder LinuxCNC + HAL Orient/PID",
    "servo_native_fixed": "Servo Drive ควบคุมตำแหน่งในตัว — Fixed / Preset",
    "servo_native_fieldbus": "Servo Drive ควบคุมตำแหน่งในตัว — Fieldbus",
    "external_controller": "ตัวควบคุมจัดแนว Spindle ภายนอก",
}

INTERFACE_LABELS = {
    "linuxcnc_m19": "อินเทอร์เฟซ LinuxCNC M19 / HAL",
    "digital_io_fixed_angle": "Digital I/O — มุมคงที่",
    "preset_select": "Digital I/O — เลือก Preset",
    "fieldbus_register": "Fieldbus / Register",
    "serial_command": "Serial / Protocol ภายนอก",
    "pulse_direction": "Pulse / Direction สำหรับควบคุมตำแหน่ง",
    "analog_position": "สั่งตำแหน่งแบบ Analog (ต้องมี DAC)",
}

PRESENTATION_LABELS = {
    "fixed": "ตำแหน่งคงที่ — ไม่มี Pot Motion แยก",
    "pot_lift": "Pot Lift — ยก / ลด",
    "pot_swing": "Pot Swing — แกว่งเข้า / ออก",
    "pot_slide": "Pot Slide — เลื่อนเข้า / ออก",
    "magazine_retract": "Magazine Retract — เลื่อนหลบ",
    "profile_defined": "กำหนดการเคลื่อนที่ตาม Profile",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _manifest_files(data_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    folder = data_dir / "examples" / "hardware-manifests"
    result = []
    for path in sorted(folder.glob("*.json")):
        try:
            result.append((path, _load_json(path)))
        except (OSError, ValueError):
            continue
    result.sort(key=lambda item: 0 if item[1].get("status") == "simulated" else 1)
    return result


if _QT_IMPORT_ERROR is None:

    class AtcWizardWidget(QWidget):
        """Reusable QWidget that can run standalone or be embedded by QtVCP."""

        def __init__(
            self,
            data_dir: str | Path,
            config: dict[str, Any] | None = None,
            parent: QWidget | None = None,
            base_config_dir: str | Path | None = None,
            output_root: str | Path | None = None,
        ) -> None:
            super().__init__(parent)
            self.data_dir = Path(data_dir).resolve()
            self.base_config_dir = Path(base_config_dir or data_dir).expanduser().resolve()
            self.output_root = (
                Path(output_root).expanduser().resolve()
                if output_root else self.base_config_dir / "generated"
            )
            self.manifests = _manifest_files(self.data_dir)
            if not self.manifests:
                raise FileNotFoundError(
                    f"No Hardware Manifest JSON files found in "
                    f"{self.data_dir / 'examples' / 'hardware-manifests'}"
                )
            initial_manifest = self.manifests[0][1]
            if config:
                saved_manifest_id = config.get("hardware", {}).get("manifest_id")
                initial_manifest = next(
                    (manifest for _path, manifest in self.manifests if manifest["manifest_id"] == saved_manifest_id),
                    initial_manifest,
                )
            self.model = WizardModel(self.data_dir, initial_manifest, config=config)
            self._building = False
            self._last_report: dict[str, Any] | None = None
            self._build_ui()
            self._refresh_all()

        def _build_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(14, 14, 14, 14)
            root.setSpacing(10)

            header = QHBoxLayout()
            title = QLabel("LinuxCNC Universal ATC — ตัวช่วยตั้งค่า")
            title.setStyleSheet("font-size: 20px; font-weight: 600;")
            self.page_counter = QLabel("ขั้นตอน 1 / 8")
            self.page_counter.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            header.addWidget(title, 1)
            header.addWidget(self.page_counter)
            root.addLayout(header)

            self.progress = QLabel("ฮาร์ดแวร์  →  ประเภท ATC  →  Magazine  →  กลไกส่งทูล  →  Feedback  →  M19  →  I/O  →  ตรวจทาน")
            self.progress.setStyleSheet("color: #687386; padding: 4px 0;")
            root.addWidget(self.progress)

            self.status_banner = QLabel(
                "โหมด Candidate เท่านั้น — ไม่มี Live Apply, Motion หรือ Physical Output"
            )
            self.status_banner.setWordWrap(True)
            self.status_banner.setStyleSheet(
                "background: #fff3cd; color: #664d03; border: 1px solid #ffecb5; "
                "border-radius: 5px; padding: 8px;"
            )
            root.addWidget(self.status_banner)

            body = QHBoxLayout()
            self.nav = QStackedWidget()
            self.pages: list[QWidget] = []
            self.nav_list = QListWidget()
            self.nav_list.setFixedWidth(145)
            for title_text in PAGE_TITLES:
                self.nav_list.addItem(title_text)
            self.nav_list.setCurrentRow(0)
            self.nav_list.currentRowChanged.connect(self._change_page)
            body.addWidget(self.nav_list)

            self.page_stack = QStackedWidget()
            self.pages = [self._build_page(index) for index in range(8)]
            for page in self.pages:
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.NoFrame)
                scroll.setWidget(page)
                self.page_stack.addWidget(scroll)
            body.addWidget(self.page_stack, 1)
            root.addLayout(body, 1)

            footer = QHBoxLayout()
            self.back_button = QPushButton("ย้อนกลับ")
            self.next_button = QPushButton("ถัดไป")
            self.save_button = QPushButton("บันทึกฉบับร่าง")
            self.back_button.clicked.connect(self._go_back)
            self.next_button.clicked.connect(self._go_next)
            self.save_button.clicked.connect(self._save_dialog)
            footer.addWidget(self.back_button)
            footer.addWidget(self.save_button)
            footer.addStretch(1)
            footer.addWidget(self.next_button)
            root.addLayout(footer)
            self._change_page(0)

            self.setMinimumSize(680, 480)

        def _page_shell(self, title: str, description: str = "") -> tuple[QWidget, QVBoxLayout]:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(16, 10, 16, 10)
            heading = QLabel(title)
            heading.setStyleSheet("font-size: 18px; font-weight: 600;")
            layout.addWidget(heading)
            if description:
                text = QLabel(description)
                text.setWordWrap(True)
                text.setStyleSheet("color: #687386;")
                layout.addWidget(text)
            layout.addStretch(1)
            return page, layout

        def _build_page(self, index: int) -> QWidget:
            if index == 0:
                page, layout = self._page_shell(
                    "หน้า 1 — Hardware / Controller",
                    "เลือก Hardware Capability Manifest ที่ตรงกับเครื่องจริง ระบบจะไม่เดา Pinout หรือจำนวน Resource จากชื่อบอร์ด",
                )
                form = QFormLayout()
                self.manifest_combo = QComboBox()
                for path, manifest in self.manifests:
                    identity = manifest["identity"]
                    label = f"{identity['controller_profile']} — {manifest['status'].upper()}"
                    self.manifest_combo.addItem(label, str(path))
                self.manifest_combo.currentIndexChanged.connect(self._on_manifest_changed)
                form.addRow("Hardware Manifest", self.manifest_combo)
                layout.insertLayout(2, form)
                self.manifest_summary = QLabel()
                self.manifest_summary.setWordWrap(True)
                self.manifest_summary.setFrameShape(QFrame.StyledPanel)
                self.manifest_summary.setMargin(10)
                layout.insertWidget(3, self.manifest_summary)
                note = QLabel(
                    "UNVERIFIED / SIMULATED ใช้ Preview และ Save Draft ได้เท่านั้น "
                    "ไม่อนุญาตให้ Apply ลงเครื่องจริง"
                )
                note.setWordWrap(True)
                layout.insertWidget(4, note)
                return page

            if index == 1:
                page, layout = self._page_shell(
                    "หน้า 2 — ATC Type",
                    "เลือกชนิด Magazine ก่อน ระบบจะแยกชนิด Magazine ออกจาก Transfer Mechanism",
                )
                form = QFormLayout()
                self.profile_combo = QComboBox()
                for profile in self.model.catalog["profiles"]:
                    self.profile_combo.addItem(
                        PROFILE_LABELS.get(profile["id"], profile["name_th"]),
                        profile["id"],
                    )
                self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
                form.addRow("ชนิด Magazine", self.profile_combo)
                layout.insertLayout(2, form)
                self.profile_summary = QLabel()
                self.profile_summary.setWordWrap(True)
                layout.insertWidget(3, self.profile_summary)
                return page

            if index == 2:
                page, layout = self._page_shell(
                    "หน้า 3 — Magazine Parameters",
                    "ตั้งค่าจำนวน Pocket, จุดอ้างอิง, ทิศทางและรูปแบบการเคลื่อนที่ ค่าทางกลจริงต้องยืนยันใน Calibration",
                )
                form = QFormLayout()
                self.pocket_count = QSpinBox()
                self.pocket_count.setRange(1, 256)
                self.pocket_count.valueChanged.connect(lambda value: self._set("atc.magazine.pocket_count", value))
                form.addRow("จำนวน Pocket", self.pocket_count)

                self.reference_pocket = QSpinBox()
                self.reference_pocket.setRange(1, 256)
                self.reference_pocket.valueChanged.connect(lambda value: self._set("atc.magazine.reference_pocket", value))
                form.addRow("Reference Pocket", self.reference_pocket)

                self.numbering_combo = self._combo(
                    [("cw", "CW"), ("ccw", "CCW"), ("forward", "Forward"), ("reverse", "Reverse"),
                     ("positive", "Positive"), ("negative", "Negative")],
                    lambda value: self._set("atc.magazine.numbering_direction", value),
                )
                form.addRow("ทิศทางหมายเลข Pocket", self.numbering_combo)

                self.direction_policy_combo = self._combo(
                    [("one_way", "One-way"), ("shortest_path", "Shortest Path")],
                    lambda value: self._set("atc.magazine.direction_policy", value),
                )
                form.addRow("นโยบายเลือกทิศทาง", self.direction_policy_combo)

                self.reversible_check = QCheckBox("ไดรฟ์สามารถกลับทิศทางได้")
                self.reversible_check.toggled.connect(lambda value: self._set("atc.magazine.reversible", value))
                form.addRow("Drive Capability", self.reversible_check)

                self.location_combo = self._combo(
                    [("fixed", "Fixed Pocket"), ("random", "Random Pocket — ยังไม่เปิดใช้ Runtime")],
                    lambda value: self._set("atc.tool_management.location_model", value),
                )
                form.addRow("การจัดเก็บ Tool", self.location_combo)

                self.drive_type_combo = self._combo(
                    [("dc_motor", "DC Motor"), ("stepper", "Stepper"), ("servo", "Servo"), ("external", "External")],
                    lambda value: self._set("atc.magazine.drive.type", value),
                )
                form.addRow("ชนิด Drive", self.drive_type_combo)

                self.drive_interface_combo = self._combo(
                    [("digital_io", "Digital I/O"), ("stepgen", "Stepgen"), ("fieldbus", "Fieldbus"), ("external_controller", "External Controller")],
                    self._on_drive_interface_changed,
                )
                form.addRow("Drive Interface", self.drive_interface_combo)

                self.linear_pitch = QDoubleSpinBox()
                self.linear_pitch.setRange(0.0, 10000.0)
                self.linear_pitch.setDecimals(3)
                self.linear_pitch.setSuffix(" mm")
                self.linear_pitch.valueChanged.connect(lambda value: self._set("atc.magazine.linear_pitch_mm", value))
                form.addRow("Linear Rack Pitch", self.linear_pitch)

                self.side_motion_combo = self._combo(
                    [("rotary", "Rotary / Drum"), ("chain", "Chain / Loop")],
                    self._on_side_mount_motion_changed,
                )
                form.addRow("Side-mounted Motion", self.side_motion_combo)

                self.disc_layout_combo = self._combo(
                    [("horizontal", "Horizontal"), ("vertical", "Vertical")],
                    lambda value: self._set("atc.magazine.disc_layout", value),
                )
                form.addRow("Rotary Disc Layout", self.disc_layout_combo)

                layout.insertLayout(2, form)
                self.magazine_note = QLabel()
                self.magazine_note.setWordWrap(True)
                layout.insertWidget(3, self.magazine_note)
                return page

            if index == 3:
                page, layout = self._page_shell(
                    "หน้า 4 — Transfer Mechanism",
                    "เลือกกลไกแลก Tool, การเคลื่อน Pot/Magazine และชนิด Drawbar แยกจากกัน",
                )
                form = QFormLayout()
                self.transfer_combo = QComboBox()
                self.transfer_combo.currentIndexChanged.connect(self._on_transfer_changed)
                form.addRow("Transfer Method", self.transfer_combo)

                self.presentation_combo = self._combo(
                    list(PRESENTATION_LABELS.items()),
                    lambda value: self._set("atc.transfer.presentation.mode", value),
                )
                form.addRow("Presentation Motion", self.presentation_combo)

                self.drawbar_combo = self._combo(
                    [("pneumatic", "Pneumatic"), ("hydraulic", "Hydraulic"), ("electric", "Electric"), ("external", "External Controller")],
                    lambda value: self._set("atc.transfer.drawbar.type", value),
                )
                form.addRow("Drawbar Type", self.drawbar_combo)

                self.drawbar_verification_combo = self._combo(
                    [("sensor", "Sensor Feedback"), ("approved_alternative", "Approved Alternative"), ("not_configured", "Not Configured")],
                    lambda value: self._set("atc.transfer.drawbar.verification_method", value),
                )
                form.addRow("Drawbar Verification", self.drawbar_verification_combo)

                self.air_pressure_check = QCheckBox("ต้องตรวจสอบแรงดันลม (Air Pressure OK)")
                self.air_pressure_check.toggled.connect(lambda value: self._set("atc.transfer.drawbar.require_air_pressure", value))
                form.addRow("Pneumatic Interlock", self.air_pressure_check)
                layout.insertLayout(2, form)
                self.transfer_signals_label = QLabel()
                self.transfer_signals_label.setWordWrap(True)
                self.transfer_signals_label.setFrameShape(QFrame.StyledPanel)
                self.transfer_signals_label.setMargin(10)
                layout.insertWidget(3, self.transfer_signals_label)
                return page

            if index == 4:
                page, layout = self._page_shell(
                    "หน้า 5 — Position Feedback & Calibration",
                    "เลือกวิธีระบุตำแหน่ง Pocket ให้ตรงกับ Sensor/Encoder ที่ติดตั้งจริง ไม่ใช้ DI ทั่วไปแทน Encoder",
                )
                form = QFormLayout()
                self.feedback_combo = QComboBox()
                self.feedback_combo.currentIndexChanged.connect(self._on_feedback_changed)
                form.addRow("Position Feedback", self.feedback_combo)

                self.encoder_combo = self._resource_combo("encoder", "atc.magazine.position_feedback.encoder_resource_id")
                form.addRow("Magazine Encoder", self.encoder_combo)

                self.bit_order_combo = self._combo(
                    [("lsb_first", "LSB First"), ("msb_first", "MSB First")],
                    lambda value: self._set("atc.magazine.position_feedback.bit_order", value),
                )
                form.addRow("Code Bit Order", self.bit_order_combo)

                self.valid_strobe_check = QCheckBox("มีสัญญาณ VALID / STROBE")
                self.valid_strobe_check.toggled.connect(lambda value: self._set("atc.magazine.position_feedback.has_valid_strobe", value))
                form.addRow("Code Sampling", self.valid_strobe_check)

                self.stable_sample = QSpinBox()
                self.stable_sample.setRange(1, 5000)
                self.stable_sample.setSuffix(" ms")
                self.stable_sample.valueChanged.connect(lambda value: self._set("atc.magazine.position_feedback.stable_sample_ms", value))
                form.addRow("Stable Sampling", self.stable_sample)
                layout.insertLayout(2, form)

                self.feedback_summary = QLabel()
                self.feedback_summary.setWordWrap(True)
                layout.insertWidget(3, self.feedback_summary)
                return page

            if index == 5:
                page, layout = self._page_shell(
                    "หน้า 6 — Spindle Orientation / M19",
                    "กำหนด Backend ของ M19 และ Resource ที่ต้องใช้ แยก Spindle Stopped ออกจาก Spindle Oriented",
                )
                form = QFormLayout()
                self.backend_combo = self._combo(list(BACKEND_LABELS.items()), self._on_backend_changed)
                form.addRow("Orientation Backend", self.backend_combo)

                self.interface_combo = QComboBox()
                self.interface_combo.currentIndexChanged.connect(self._on_interface_changed)
                form.addRow("Command Interface", self.interface_combo)

                self.target_mode_combo = self._combo(
                    [("fixed", "Fixed Angle"), ("preset", "Preset"), ("variable", "Variable Target")],
                    lambda value: self._set("atc.spindle_orientation.target_mode", value),
                )
                form.addRow("Target Mode", self.target_mode_combo)

                self.angle_spin = QDoubleSpinBox()
                self.angle_spin.setRange(0.0, 359.999)
                self.angle_spin.setDecimals(3)
                self.angle_spin.setSuffix(" deg")
                self.angle_spin.valueChanged.connect(lambda value: self._set("atc.spindle_orientation.fixed_angle_deg", value))
                form.addRow("Target Angle", self.angle_spin)

                self.offset_spin = QDoubleSpinBox()
                self.offset_spin.setRange(-360.0, 360.0)
                self.offset_spin.setDecimals(3)
                self.offset_spin.setSuffix(" deg")
                self.offset_spin.valueChanged.connect(lambda value: self._set("atc.spindle_orientation.orientation_offset_deg", value))
                form.addRow("Orientation Offset", self.offset_spin)

                self.tolerance_spin = QDoubleSpinBox()
                self.tolerance_spin.setRange(0.001, 180.0)
                self.tolerance_spin.setDecimals(3)
                self.tolerance_spin.setSuffix(" deg")
                self.tolerance_spin.valueChanged.connect(lambda value: self._set("atc.spindle_orientation.tolerance_deg", value))
                form.addRow("Position Tolerance", self.tolerance_spin)

                self.timeout_spin = QSpinBox()
                self.timeout_spin.setRange(1, 600000)
                self.timeout_spin.setSuffix(" ms")
                self.timeout_spin.valueChanged.connect(lambda value: self._set("atc.spindle_orientation.timeout_ms", value))
                form.addRow("M19 Timeout", self.timeout_spin)

                self.spindle_encoder_combo = self._resource_combo("encoder", "atc.spindle_orientation.resources.encoder_resource_id")
                form.addRow("Spindle Encoder", self.spindle_encoder_combo)

                self.spindle_comm_combo = self._resource_combo("communication", "atc.spindle_orientation.resources.communication_resource_id")
                form.addRow("Communication Resource", self.spindle_comm_combo)

                self.spindle_position_combo = QComboBox()
                self.spindle_position_combo.currentIndexChanged.connect(
                    lambda _: self._set("atc.spindle_orientation.resources.position_command_resource_id", self.spindle_position_combo.currentData())
                )
                form.addRow("Position Command Resource", self.spindle_position_combo)

                self.zero_speed_check = QCheckBox("ต้องยืนยันความเร็วเป็นศูนย์ (Zero Speed)")
                self.zero_speed_check.toggled.connect(lambda value: self._set("atc.spindle_orientation.require_zero_speed", value))
                form.addRow("Spindle Interlock", self.zero_speed_check)

                self.brake_check = QCheckBox("ต้องมี Feedback ยืนยันว่า Brake จับอยู่")
                self.brake_check.toggled.connect(lambda value: self._set("atc.spindle_orientation.require_brake_feedback", value))
                form.addRow("Mechanical Brake", self.brake_check)

                layout.insertLayout(2, form)
                self.m19_note = QLabel()
                self.m19_note.setWordWrap(True)
                layout.insertWidget(3, self.m19_note)
                return page

            if index == 6:
                page, layout = self._page_shell(
                    "หน้า 7 — I/O Mapping & Resource Assignment",
                    "Auto-map จัดสรรเฉพาะ Physical DI/DO ที่ Manifest ระบุว่า Available และ Verified; Encoder/Stepgen/Bus เลือกแยกตามชนิด",
                )
                actions = QHBoxLayout()
                auto_button = QPushButton("จัดสรร I/O อัตโนมัติ (Required / Optional)")
                auto_button.clicked.connect(self._auto_map)
                actions.addWidget(auto_button)
                actions.addStretch(1)
                layout.insertLayout(2, actions)

                self.io_table = QTableWidget(0, 5)
                self.io_table.setHorizontalHeaderLabels(["Logical Signal", "Requirement", "Direction", "Physical Resource", "Active Level"])
                self.io_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
                self.io_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
                self.io_table.setAlternatingRowColors(True)
                self.io_table.setMinimumHeight(260)
                layout.insertWidget(3, self.io_table, 1)

                resource_group = QGroupBox("ทรัพยากร Motion / Encoder / Communication")
                resource_form = QFormLayout(resource_group)
                self.magazine_stepgen_combo = self._resource_combo("stepgen", "atc.motion_resources.magazine_motion")
                resource_form.addRow("Magazine Stepgen", self.magazine_stepgen_combo)
                layout.insertWidget(4, resource_group)

                self.mapping_summary = QLabel()
                self.mapping_summary.setWordWrap(True)
                layout.insertWidget(5, self.mapping_summary)
                return page

            page, layout = self._page_shell(
                "หน้า 8 — Review / Validate / Apply",
                "ตรวจ Configuration แล้วสร้างสำเนา LinuxCNC Axis Simulation แยกโฟลเดอร์ได้ โดยไม่แก้เครื่องเดิมและไม่สั่ง Hardware",
            )
            self.review_text = QLabel()
            self.review_text.setWordWrap(True)
            self.review_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.review_text.setFrameShape(QFrame.StyledPanel)
            self.review_text.setMargin(10)
            layout.insertWidget(2, self.review_text)

            buttons = QHBoxLayout()
            validate_button = QPushButton("ตรวจสอบ Configuration")
            validate_button.clicked.connect(self._validate)
            buttons.addWidget(validate_button)
            self.apply_button = QPushButton("สร้าง Configuration สำหรับทดสอบ")
            self.apply_button.setToolTip(
                "สร้างสำเนา Axis Simulation พร้อมค่า ATC ในโฟลเดอร์ใหม่เท่านั้น "
                "ไม่ Apply เข้าเครื่องจริงและไม่สั่ง Physical I/O"
            )
            self.apply_button.clicked.connect(self._apply_candidate)
            self.apply_button.setEnabled(False)
            buttons.addWidget(self.apply_button)
            layout.insertLayout(3, buttons)

            self.validation_text = QLabel("ยังไม่ได้ตรวจสอบ Configuration")
            self.validation_text.setWordWrap(True)
            self.validation_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.validation_text.setFrameShape(QFrame.StyledPanel)
            self.validation_text.setMargin(10)
            layout.insertWidget(4, self.validation_text, 1)
            return page

        def _combo(self, items: list[tuple[str, str]], callback: Any) -> QComboBox:
            combo = QComboBox()
            for value, label in items:
                combo.addItem(label, value)
            combo.currentIndexChanged.connect(lambda _: callback(combo.currentData()))
            return combo

        def _resource_combo(self, resource_type: str, path: str) -> QComboBox:
            combo = QComboBox()
            combo.addItem("— ยังไม่เลือก —", "")
            combo.currentIndexChanged.connect(lambda _: self._set(path, combo.currentData() or None))
            combo._atc_resource_type = resource_type  # type: ignore[attr-defined]
            combo._atc_path = path  # type: ignore[attr-defined]
            return combo

        def _set_combo(self, combo: QComboBox, value: Any) -> None:
            index = combo.findData(value)
            if index >= 0:
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)

        def _invalidate_report(self) -> None:
            self._last_report = None
            if hasattr(self, "apply_button"):
                self.apply_button.setEnabled(False)

        def _set(self, path: str, value: Any) -> None:
            if self._building:
                return
            self.model.set_value(path, value)
            self._invalidate_report()
            if path == "atc.magazine.pocket_count":
                self.reference_pocket.setMaximum(max(1, int(value)))
            if hasattr(self, "io_table") and path.startswith(("atc.magazine.", "atc.transfer.", "atc.spindle_orientation.")):
                self._refresh_io_table()
            self._refresh_review_summary()

        def _on_manifest_changed(self, index: int) -> None:
            if index < 0:
                return
            path = Path(self.manifest_combo.itemData(index))
            manifest = _load_json(path)
            self.model.set_manifest(manifest)
            self._invalidate_report()
            self._refresh_all()

        def _on_profile_changed(self, index: int) -> None:
            if index < 0:
                return
            self.model.set_profile(str(self.profile_combo.itemData(index)))
            self._invalidate_report()
            self._refresh_all()

        def _on_drive_interface_changed(self, value: str) -> None:
            self.model.set_value("atc.magazine.drive.interface", value)
            self._invalidate_report()
            self._refresh_all()

        def _on_side_mount_motion_changed(self, value: str) -> None:
            self.model.set_value("atc.magazine.side_mount_motion", value)
            self._invalidate_report()
            self._refresh_all()

        def _on_transfer_changed(self, index: int) -> None:
            if index < 0:
                return
            value = self.transfer_combo.itemData(index)
            self.model.set_value("atc.transfer.mechanism", value)
            if value == "pot_movement":
                self.model.set_value("atc.transfer.presentation.mode", "pot_lift")
            self._invalidate_report()
            self._refresh_all()

        def _on_feedback_changed(self, index: int) -> None:
            if index < 0:
                return
            self.model.set_value("atc.magazine.position_feedback.method", self.feedback_combo.itemData(index))
            self._invalidate_report()
            self._refresh_all()

        def _on_backend_changed(self, value: str) -> None:
            defaults = {
                "linuxcnc_encoder_pid": ("linuxcnc_m19", "fixed"),
                "servo_native_fixed": ("digital_io_fixed_angle", "fixed"),
                "servo_native_fieldbus": ("fieldbus_register", "variable"),
                "external_controller": ("serial_command", "variable"),
            }
            interface, target_mode = defaults[value]
            self.model.set_value("atc.spindle_orientation.backend", value)
            self.model.set_value("atc.spindle_orientation.command_interface", interface)
            self.model.set_value("atc.spindle_orientation.target_mode", target_mode)
            self._invalidate_report()
            self._refresh_all()

        def _on_interface_changed(self, value: str) -> None:
            if not value:
                return
            self.model.set_value("atc.spindle_orientation.command_interface", value)
            target_mode = "preset" if value == "preset_select" else (
                "fixed" if value == "digital_io_fixed_angle" else "variable"
            )
            self.model.set_value("atc.spindle_orientation.target_mode", target_mode)
            self._invalidate_report()
            self._refresh_all()

        def _refresh_all(self) -> None:
            self._building = True
            config = self.model.config
            atc = config["atc"]
            self._set_combo(self.manifest_combo, next(
                (str(path) for path, manifest in self.manifests if manifest["manifest_id"] == self.model.manifest["manifest_id"]),
                "",
            ))
            self._set_combo(self.profile_combo, atc["profile_id"])

            identity = self.model.manifest["identity"]
            resources = self.model.manifest["resources"]
            counts: dict[str, int] = {}
            for resource in resources:
                counts[resource["type"]] = counts.get(resource["type"], 0) + 1
            self.manifest_summary.setText(
                f"<b>สถานะ:</b> {self.model.manifest['status'].upper()}<br>"
                f"<b>Controller:</b> {identity['controller_profile']}<br>"
                f"<b>Board Revision:</b> {identity['board_revision']}<br>"
                f"<b>HostMot2:</b> {identity['hostmot2_firmware_id']}<br>"
                f"<b>LinuxCNC:</b> {identity['linuxcnc_version']}<br>"
                f"<b>Resources:</b> " + ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
            )
            self.profile_summary.setText(
                f"Magazine Type: {self.model.profile['magazine_type']} | "
                f"Pocket range ใน Profile: {self.model.profile['pocket_count']['min']}–{self.model.profile['pocket_count']['max']} "
                f"(ขีดจำกัดนี้เป็นข้อมูล Profile รุ่นทดลอง ไม่ใช่การรับรองกลไกจริง)"
            )

            magazine = atc["magazine"]
            self.pocket_count.setValue(magazine["pocket_count"])
            self.reference_pocket.setMaximum(magazine["pocket_count"])
            self.reference_pocket.setValue(min(magazine.get("reference_pocket", 1), magazine["pocket_count"]))
            numbering_type = magazine["type"]
            if numbering_type == "chain" or (numbering_type == "side_mounted" and magazine.get("side_mount_motion") == "chain"):
                numbering_options = [("forward", "Forward"), ("reverse", "Reverse")]
                numbering_default = "forward"
            elif numbering_type == "linear_rack":
                numbering_options = [("positive", "Positive"), ("negative", "Negative")]
                numbering_default = "positive"
            else:
                numbering_options = [("cw", "CW"), ("ccw", "CCW")]
                numbering_default = "cw"
            self.numbering_combo.blockSignals(True)
            self.numbering_combo.clear()
            for value, label in numbering_options:
                self.numbering_combo.addItem(label, value)
            self._set_combo(self.numbering_combo, magazine.get("numbering_direction", numbering_default))
            self.numbering_combo.blockSignals(False)
            self._set_combo(self.direction_policy_combo, magazine.get("direction_policy", "one_way"))
            self.reversible_check.setChecked(magazine.get("reversible", False))
            self._set_combo(self.location_combo, atc["tool_management"]["location_model"])
            self._set_combo(self.drive_type_combo, magazine["drive"]["type"])
            self._set_combo(self.drive_interface_combo, magazine["drive"]["interface"])
            self.linear_pitch.setValue(magazine.get("linear_pitch_mm", 0.0))
            self._set_combo(self.side_motion_combo, magazine.get("side_mount_motion", "rotary"))
            self._set_combo(self.disc_layout_combo, magazine.get("disc_layout", "horizontal"))
            self.linear_pitch.setVisible(magazine["type"] == "linear_rack")
            self.side_motion_combo.setVisible(magazine["type"] == "side_mounted")
            self.disc_layout_combo.setVisible(magazine["type"] == "rotary_disc")
            self.magazine_note.setText(
                "Shortest Path ใช้ได้เมื่อเลือก Drive แบบ Reversible เท่านั้น. "
                "Random Pocket จะถูก Block จนกว่าจะมี Runtime Tool Location Manager และ Recovery ที่ผ่านการทดสอบ."
            )

            transfer = atc["transfer"]
            self.transfer_combo.blockSignals(True)
            self.transfer_combo.clear()
            for value in self.model.profile["supported_transfer_mechanisms"]:
                self.transfer_combo.addItem(TRANSFER_LABELS.get(value, value), value)
            self._set_combo(self.transfer_combo, transfer["mechanism"])
            self.transfer_combo.blockSignals(False)
            mechanism = transfer["mechanism"]
            if mechanism == "pot_movement":
                presentation_options = [("pot_lift", PRESENTATION_LABELS["pot_lift"]), ("pot_swing", PRESENTATION_LABELS["pot_swing"]), ("pot_slide", PRESENTATION_LABELS["pot_slide"])]
            elif mechanism in ("single_arm", "double_arm_180"):
                presentation_options = [("fixed", PRESENTATION_LABELS["fixed"]), ("magazine_retract", PRESENTATION_LABELS["magazine_retract"]), ("profile_defined", PRESENTATION_LABELS["profile_defined"])]
            else:
                presentation_options = list(PRESENTATION_LABELS.items())
            self.presentation_combo.blockSignals(True)
            self.presentation_combo.clear()
            for value, label in presentation_options:
                self.presentation_combo.addItem(label, value)
            self._set_combo(self.presentation_combo, transfer.get("presentation", {}).get("mode", "fixed"))
            self.presentation_combo.blockSignals(False)
            drawbar = transfer.get("drawbar", {})
            self._set_combo(self.drawbar_combo, drawbar.get("type", "pneumatic"))
            self._set_combo(self.drawbar_verification_combo, drawbar.get("verification_method", "sensor"))
            self.air_pressure_check.setChecked(drawbar.get("require_air_pressure", False))
            specs = self.model.signal_specs()
            self.transfer_signals_label.setText(
                "<b>Logical Signals ที่สร้างจากตัวเลือกปัจจุบัน</b><br>" +
                ", ".join(item["id"] for item in specs)
            )

            feedback = magazine["position_feedback"]
            self.feedback_combo.blockSignals(True)
            self.feedback_combo.clear()
            for value in self.model.profile["supported_position_feedback"]:
                self.feedback_combo.addItem(FEEDBACK_LABELS.get(value, value), value)
            self._set_combo(self.feedback_combo, feedback["method"])
            self.feedback_combo.blockSignals(False)
            self._populate_resource_combo(self.encoder_combo, "encoder", feedback.get("encoder_resource_id", ""))
            self._set_combo(self.bit_order_combo, feedback.get("bit_order", "lsb_first"))
            self.valid_strobe_check.setChecked(feedback.get("has_valid_strobe", False))
            self.stable_sample.setValue(feedback.get("stable_sample_ms", 50))
            self.encoder_combo.setVisible(feedback["method"] in ("incremental_encoder", "absolute_encoder"))
            self.feedback_summary.setText(
                f"Logical signals: {', '.join(item['id'] for item in specs if item['id'].startswith(('MAG_', 'POT_')))}"
            )

            spindle = atc["spindle_orientation"]
            self._set_combo(self.backend_combo, spindle["backend"])
            self._populate_interface_combo(spindle["backend"], spindle["command_interface"])
            self._set_combo(self.target_mode_combo, spindle["target_mode"])
            self.angle_spin.setValue(spindle.get("fixed_angle_deg", 180.0))
            self.offset_spin.setValue(spindle.get("orientation_offset_deg", 0.0))
            self.tolerance_spin.setValue(spindle.get("tolerance_deg", 1.0))
            self.timeout_spin.setValue(spindle.get("timeout_ms", 8000))
            spindle_resources = spindle.get("resources", {})
            self._populate_resource_combo(self.spindle_encoder_combo, "encoder", spindle_resources.get("encoder_resource_id", ""))
            self._populate_resource_combo(self.spindle_comm_combo, "communication", spindle_resources.get("communication_resource_id", ""))
            position_resource_type = "dac" if spindle["command_interface"] == "analog_position" else "stepgen"
            self._populate_resource_combo(self.spindle_position_combo, position_resource_type, spindle_resources.get("position_command_resource_id", ""))
            self.spindle_encoder_combo.setVisible(spindle["backend"] == "linuxcnc_encoder_pid")
            self.spindle_comm_combo.setVisible(spindle["backend"] in ("servo_native_fieldbus", "external_controller") and spindle["command_interface"] in ("fieldbus_register", "serial_command"))
            self.spindle_position_combo.setVisible(spindle["command_interface"] in ("pulse_direction", "analog_position"))
            self.zero_speed_check.setChecked(spindle.get("require_zero_speed", True))
            self.brake_check.setChecked(spindle.get("require_brake_feedback", False))
            self.m19_note.setText(
                "LinuxCNC M19 เป็น Internal HAL Handshake ไม่ใช่ Physical DO. "
                "Target Angle และ In-position ต้องมาจาก Backend/Feedback ที่เลือก; Timer เพียงอย่างเดียวไม่ยืนยัน Orientation."
            )

            self._populate_resource_combo(self.magazine_stepgen_combo, "stepgen", atc.get("motion_resources", {}).get("magazine_motion", ""))
            self.magazine_stepgen_combo.setVisible(magazine["drive"]["interface"] == "stepgen")
            self._refresh_io_table()
            self._refresh_review_summary()
            self._building = False

        def _populate_resource_combo(self, combo: QComboBox, resource_type: str, selected: str) -> None:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("— ยังไม่เลือก —", "")
            for resource in self.model.resource_options(resource_type):
                label = resource["id"]
                if resource.get("connector"):
                    label += f" ({resource['connector']})"
                combo.addItem(label, resource["id"])
            self._set_combo(combo, selected or "")
            combo.blockSignals(False)

        def _populate_interface_combo(self, backend: str, selected: str) -> None:
            options = {
                "linuxcnc_encoder_pid": ["linuxcnc_m19"],
                "servo_native_fixed": ["digital_io_fixed_angle", "preset_select"],
                "servo_native_fieldbus": ["fieldbus_register"],
                "external_controller": ["serial_command", "fieldbus_register", "pulse_direction", "analog_position"],
            }[backend]
            self.interface_combo.blockSignals(True)
            self.interface_combo.clear()
            for value in options:
                self.interface_combo.addItem(INTERFACE_LABELS[value], value)
            self._set_combo(self.interface_combo, selected)
            self.interface_combo.blockSignals(False)

        def _refresh_io_table(self) -> None:
            specs = self.model.signal_specs()
            mapping = self.model.config["atc"]["io_mapping"]
            self.io_table.setRowCount(len(specs))
            for row, spec in enumerate(specs):
                self.io_table.setItem(row, 0, QTableWidgetItem(spec["id"]))
                self.io_table.setItem(row, 1, QTableWidgetItem(spec["requirement"].upper()))
                self.io_table.setItem(row, 2, QTableWidgetItem("DI" if spec["direction"] == "input" else "DO"))

                resource_type = "digital_input" if spec["direction"] == "input" else "digital_output"
                resource_combo = QComboBox()
                resource_combo.addItem("— ไม่ได้กำหนด —", "")
                for resource in self.model.resource_options(resource_type):
                    resource_combo.addItem(resource["id"], resource["id"])
                current = mapping.get(spec["id"], {}).get("resource_id", "")
                self._set_combo(resource_combo, current)
                resource_combo.currentIndexChanged.connect(
                    lambda _index, signal=spec["id"], combo=resource_combo:
                    self._on_io_resource_changed(signal, combo)
                )
                self.io_table.setCellWidget(row, 3, resource_combo)

                level_combo = QComboBox()
                level_combo.addItem("Active High (ระดับสัญญาณสูง)", "high")
                level_combo.addItem("Active Low (ระดับสัญญาณต่ำ)", "low")
                current_level = mapping.get(spec["id"], {}).get("active_level", "high")
                self._set_combo(level_combo, current_level)
                level_combo.currentIndexChanged.connect(
                    lambda _index, signal=spec["id"], resource=resource_combo, level=level_combo:
                    self._on_io_level_changed(signal, resource, level)
                )
                self.io_table.setCellWidget(row, 4, level_combo)
            self.io_table.resizeRowsToContents()
            assigned = len(mapping)
            required = sum(1 for spec in specs if spec["requirement"] in ("required", "conditional"))
            mapped_required = sum(
                1 for spec in specs
                if spec["requirement"] in ("required", "conditional") and spec["id"] in mapping
            )
            self.mapping_summary.setText(
                f"Mapped: {assigned}/{len(specs)} signals | Required/Conditional mapped: {mapped_required}/{required}"
            )
            self._refresh_review_summary()

        def _on_io_resource_changed(self, signal_id: str, combo: QComboBox) -> None:
            if self._building:
                return
            current = self.model.config["atc"]["io_mapping"].get(signal_id, {})
            self.model.set_io_mapping(signal_id, combo.currentData() or None, current.get("active_level", "high"))
            self._invalidate_report()
            self._refresh_io_summary_only()

        def _on_io_level_changed(self, signal_id: str, resource_combo: QComboBox, level_combo: QComboBox) -> None:
            if self._building:
                return
            self.model.set_io_mapping(signal_id, resource_combo.currentData() or None, level_combo.currentData())
            self._invalidate_report()
            self._refresh_io_summary_only()

        def _refresh_io_summary_only(self) -> None:
            mapping = self.model.config["atc"]["io_mapping"]
            specs = self.model.signal_specs()
            required = sum(1 for spec in specs if spec["requirement"] in ("required", "conditional"))
            mapped_required = sum(
                1 for spec in specs
                if spec["requirement"] in ("required", "conditional") and spec["id"] in mapping
            )
            self.mapping_summary.setText(
                f"Mapped: {len(mapping)}/{len(specs)} signals | Required/Conditional mapped: {mapped_required}/{required}"
            )
            self._refresh_review_summary()

        def _auto_map(self) -> None:
            result = self.model.auto_assign_io()
            self._invalidate_report()
            self._refresh_io_table()
            message = f"Auto-map เสร็จ: Required ที่ยังไม่ได้ Map {len(result['unmapped_required'])} รายการ"
            if result["unmapped_required"]:
                message += "\n" + ", ".join(result["unmapped_required"])
            QMessageBox.information(self, "จัดสรร I/O ATC อัตโนมัติ", message)

        def _refresh_review_summary(self) -> None:
            if not hasattr(self, "review_text"):
                return
            atc = self.model.config["atc"]
            magazine = atc["magazine"]
            transfer = atc["transfer"]
            spindle = atc["spindle_orientation"]
            profile = self.model.profile
            self.review_text.setText(
                f"<b>ฮาร์ดแวร์:</b> {self.model.manifest['identity']['controller_profile']} "
                f"({self.model.manifest['status'].upper()})<br>"
                f"<b>ประเภท ATC:</b> {PROFILE_LABELS.get(profile['id'], profile['name_th'])}<br>"
                f"<b>จำนวน Pocket:</b> {magazine['pocket_count']} | จุดอ้างอิง: {magazine.get('reference_pocket', 1)} | "
                f"Feedback: {FEEDBACK_LABELS.get(magazine['position_feedback']['method'], magazine['position_feedback']['method'])}<br>"
                f"<b>กลไกส่งทูล:</b> {TRANSFER_LABELS.get(transfer['mechanism'], transfer['mechanism'])} | "
                f"รูปแบบการเคลื่อนที่: {PRESENTATION_LABELS.get(transfer.get('presentation', {}).get('mode', 'fixed'))}<br>"
                f"<b>ตำแหน่งจัดเก็บ Tool:</b> {atc['tool_management']['location_model']}<br>"
                f"<b>M19:</b> {BACKEND_LABELS[spindle['backend']]} | "
                f"{INTERFACE_LABELS[spindle['command_interface']]} | "
                f"มุมเป้าหมาย: {spindle.get('fixed_angle_deg', 'Variable')}°<br>"
                f"<b>การกำหนด I/O:</b> {len(atc['io_mapping'])} assignments<br>"
                f"<b>ความปลอดภัย:</b> ATC Enable = ปิด; Live Apply = ปิด"
            )

        def _validate(self) -> None:
            report = self.model.validate()
            self._last_report = report
            summary = report["summary"]
            lines = [
                f"Configuration ถูกต้อง: {'YES' if report['configuration_valid'] else 'NO'}",
                f"อนุญาต Live Apply: {'YES' if report['live_apply_allowed'] else 'NO'}",
                f"รายการขัดขวาง {summary['blocker']} | ข้อผิดพลาด {summary['error']} | คำเตือน {summary['warning']} | ข้อมูล {summary['info']}",
                "",
            ]
            for finding in report["findings"]:
                page = finding.get("go_to_page")
                location = f" (หน้า {page})" if page else ""
                lines.append(f"[{finding['severity'].upper()}] {finding['id']}{location}")
                lines.append(f"  {finding['message_th']}")
            if not report["findings"]:
                lines.append("ไม่พบปัญหาตามกฎ Validation ที่มีใน Prototype")
            self.validation_text.setText("\n".join(lines))
            has_axis_base = (self.base_config_dir / "axis.ini").is_file()
            self.apply_button.setEnabled(bool(report["configuration_valid"] and has_axis_base))
            if not has_axis_base:
                self.status_banner.setText(
                    "Validate เสร็จแล้ว แต่ยังไม่มี axis.ini ในโฟลเดอร์นี้ จึงสร้าง LinuxCNC Candidate ไม่ได้"
                )
            elif report["configuration_valid"]:
                self.status_banner.setText(
                    "Configuration ผ่านการตรวจเชิงโครงสร้าง — การสร้าง Candidate จะทำสำเนา Axis Simulation ใหม่เท่านั้น "
                    "ไม่ใช่ Live Apply และ ATC ยังคงปิดอยู่"
                )
            else:
                self.status_banner.setText(
                    "Configuration ยังมีข้อผิดพลาด — กรุณาแก้ไขรายการที่แจ้งก่อนสร้าง Candidate"
                )

        def _apply_candidate(self) -> None:
            report = self._last_report
            if report is None or not report.get("configuration_valid"):
                QMessageBox.warning(self, "ยังสร้างคอนฟิกไม่ได้", "กรุณาตรวจสอบ Configuration ใหม่ก่อน")
                self._invalidate_report()
                return
            try:
                target = generate_candidate(
                    self.model.config,
                    self.model.manifest,
                    report,
                    self.base_config_dir,
                    self.output_root,
                    data_dir=self.data_dir,
                )
            except Exception as exc:
                QMessageBox.critical(self, "สร้าง Configuration ไม่สำเร็จ", str(exc))
                return
            self.status_banner.setText(
                f"สร้าง Simulation Candidate แล้ว: {target}. ATC Enable = OFF; Live Apply = OFF"
            )
            QMessageBox.information(
                self,
                "สร้าง LinuxCNC Candidate สำเร็จ",
                "สร้างสำเนา Configuration แยกจากเครื่องต้นฉบับแล้ว\n\n"
                f"{target}\n\n"
                "ไฟล์หลัก: axis.ini, atc_config.json, atc_validation.json, "
                "atc_io_map.csv และ atc_generated.hal\n\n"
                "เปิดทดสอบด้วยคำสั่ง:\n"
                f"linuxcnc {target / 'axis.ini'}\n\n"
                "นี่เป็น Axis Simulation Candidate เท่านั้น ยังไม่มี ATC Runtime "
                "และไม่มีคำสั่ง Physical Output/Motion",
            )

        def _save_dialog(self) -> None:
            default_path = Path.home() / ".config" / "linuxcnc" / "universal-atc" / "atc-config.json"
            path, _ = QFileDialog.getSaveFileName(
                self, "บันทึก ATC Configuration Draft", str(default_path), "ATC JSON (*.json)"
            )
            if not path:
                return
            try:
                saved = self.model.save(path)
            except OSError as exc:
                QMessageBox.critical(self, "บันทึกไม่สำเร็จ", str(exc))
                return
            QMessageBox.information(self, "บันทึกฉบับร่าง", f"บันทึก Configuration แล้ว:\n{saved}")

        def _change_page(self, index: int) -> None:
            if index < 0 or index >= 8:
                return
            self.page_stack.setCurrentIndex(index)
            self.page_counter.setText(f"ขั้นตอน {index + 1} / 8")
            self.back_button.setEnabled(index > 0)
            self.next_button.setEnabled(index < 7)
            if index == 7:
                self._refresh_review_summary()

        def _go_back(self) -> None:
            index = self.page_stack.currentIndex()
            if index > 0:
                self.nav_list.setCurrentRow(index - 1)

        def _go_next(self) -> None:
            index = self.page_stack.currentIndex()
            if index < 7:
                self.nav_list.setCurrentRow(index + 1)

    def main(argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(description="LinuxCNC Universal ATC Setup Wizard prototype")
        parser.add_argument("--data-dir", default=".", help="Repository/data root containing schemas/, profiles/ and examples/")
        parser.add_argument("--config", help="Optional existing ATC JSON draft")
        parser.add_argument(
            "--base-config-dir",
            help="LinuxCNC configuration directory containing axis.ini; enables Apply to generate an isolated candidate",
        )
        parser.add_argument(
            "--output-root",
            help="Writable directory for generated candidates (default: ~/linuxcnc/configs/universal-atc-generated)",
        )
        args = parser.parse_args(argv)
        data_dir = Path(args.data_dir).expanduser().resolve()
        base_config_dir = (
            Path(args.base_config_dir).expanduser().resolve()
            if args.base_config_dir else data_dir
        )
        output_root = (
            Path(args.output_root).expanduser().resolve()
            if args.output_root
            else Path.home() / "linuxcnc" / "configs" / "universal-atc-generated"
        )
        if not (data_dir / "schemas" / "atc-config.schema.json").exists():
            candidate = Path(__file__).resolve().parents[2]
            if (candidate / "schemas" / "atc-config.schema.json").exists():
                data_dir = candidate
        manifests = _manifest_files(data_dir)
        if not manifests:
            raise SystemExit(f"No manifests found under {data_dir / 'examples' / 'hardware-manifests'}")
        config = WizardModel.load_config(args.config) if args.config else None
        app = QApplication(sys.argv[:1])
        window = QMainWindow()
        window.setWindowTitle("LinuxCNC Universal ATC — ตัวตั้งค่า ATC")
        window.setCentralWidget(
            AtcWizardWidget(
                data_dir,
                config=config,
                base_config_dir=base_config_dir,
                output_root=output_root,
            )
        )
        window.resize(1180, 820)
        window.show()
        return app.exec_()

else:

    class AtcWizardWidget:  # pragma: no cover - only used to provide a clear error
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("PyQt5 is required. On Debian/LinuxCNC install: sudo apt install python3-pyqt5")


    def main(argv: list[str] | None = None) -> int:
        raise SystemExit("PyQt5 is required. On Debian/LinuxCNC install: sudo apt install python3-pyqt5")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
