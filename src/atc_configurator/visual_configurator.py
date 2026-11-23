"""Beginner focused visual ATC configurator for QtVCP and QtDragon."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .generator import generate_candidate
from .gui import (
    FEEDBACK_LABELS,
    PROFILE_LABELS,
    TRANSFER_LABELS,
    _manifest_files,
)
from .wizard_model import WizardModel
from .sim_runtime import SimRuntime, STEP_LABELS


SIGNAL_HELP = {
    "MAG_HOME": "เซ็นเซอร์อ้างอิงตำแหน่งศูนย์ของแมกกาซีน ใช้เริ่มนับ Pocket ใหม่หลังเปิดเครื่อง",
    "MAG_INDEX": "พัลส์ยืนยันว่าแมกกาซีนเลื่อนผ่านหนึ่งตำแหน่ง",
    "MAG_IN_POSITION": "ยืนยันว่า Pocket ที่เรียกมาถึงตำแหน่งเปลี่ยนทูลแล้ว",
    "ARM_HOME": "ยืนยันว่าแขนเปลี่ยนทูลกลับถึงตำแหน่งพักที่ปลอดภัย",
    "ARM_AT_EXCHANGE": "ยืนยันว่าแขนอยู่ตรงตำแหน่งรับและส่งทูล",
    "ARM_180_POSITION": "ยืนยันว่าแขนหมุนครบ 180 องศาแล้ว",
    "ARM_AT_SPINDLE": "ยืนยันว่าแขนอยู่ฝั่งสปินเดิล",
    "ARM_AT_MAGAZINE": "ยืนยันว่าแขนอยู่ฝั่งแมกกาซีน",
    "TOOL_PRESENT_SPINDLE": "เซ็นเซอร์ตรวจว่ามี Tool อยู่ในสปินเดิล",
    "DRAWBAR_CLAMPED": "ยืนยันว่า Drawbar จับ Tool แน่นแล้ว",
    "DRAWBAR_UNCLAMPED": "ยืนยันว่า Drawbar ปล่อย Tool แล้ว",
    "AIR_PRESSURE_OK": "ยืนยันว่าแรงดันลมเพียงพอก่อนเริ่มเปลี่ยนทูล",
    "MAGAZINE_EXTENDED": "ลิมิตยืนยันว่ากระบอกพาแมกกาซีนเข้าถึงตำแหน่งเปลี่ยนทูลแล้ว",
    "MAGAZINE_RETRACTED": "ลิมิตยืนยันว่าแมกกาซีนถอยกลับถึงตำแหน่งปลอดภัยแล้ว",
    "ATC_DOOR_OPEN": "ลิมิตยืนยันว่าประตูครอบจานทูลเปิดสุดแล้ว",
    "ATC_DOOR_CLOSED": "ลิมิตยืนยันว่าประตูครอบจานทูลปิดสนิทแล้ว",
    "SPINDLE_ORIENT_IN_POSITION": "ยืนยันว่า M19 หมุนสปินเดิลถึงมุมที่ตั้งไว้",
    "SPINDLE_ZERO_SPEED": "ยืนยันว่าสปินเดิลหยุดสนิทก่อนแขนเข้าทำงาน",
    "SPINDLE_DRIVE_READY": "ไดรฟ์สปินเดิลพร้อมรับคำสั่ง",
    "SPINDLE_DRIVE_FAULT": "สัญญาณแจ้ง Fault จากไดรฟ์สปินเดิล",
    "GRIPPER_A_TOOL_PRESENT": "ตรวจว่ากริปเปอร์ A จับ Tool อยู่",
    "GRIPPER_B_TOOL_PRESENT": "ตรวจว่ากริปเปอร์ B จับ Tool อยู่",
    "GRIPPER_A_CLOSED": "ยืนยันว่ากริปเปอร์ A ปิดและจับ Tool แล้ว",
    "GRIPPER_B_CLOSED": "ยืนยันว่ากริปเปอร์ B ปิดและจับ Tool แล้ว",
}


def _friendly_signal(signal_id: str) -> str:
    replacements = {
        "CMD": "Command",
        "CW": "Clockwise",
        "CCW": "Counter-clockwise",
        "MAG": "Magazine",
    }
    words = [replacements.get(part, part.title()) for part in signal_id.split("_")]
    return " ".join(words)


def _signal_help(signal_id: str, direction: str) -> str:
    if signal_id in SIGNAL_HELP:
        return SIGNAL_HELP[signal_id]
    if signal_id.startswith(("MAG_CODE_BIT_", "MAG_BCD_BIT_")):
        return "บิตตำแหน่งจากเซ็นเซอร์รหัสของแมกกาซีน ใช้รวมกันเพื่ออ่านหมายเลข Pocket"
    if signal_id.startswith("MAG_POCKET_"):
        return "เซ็นเซอร์ประจำ Pocket ใช้ยืนยัน Pocket หมายเลขนี้โดยตรง"
    if direction == "output":
        return "เอาต์พุตคำสั่งจาก LinuxCNC ไปยังอุปกรณ์นี้ ตรวจชนิดวงจรและ Active Level ก่อนใช้งานจริง"
    return "อินพุตยืนยันสถานะจากเซ็นเซอร์ เลือกขา I/O ที่ต่อสายจริงกับสัญญาณนี้"


class AtcDiagramWidget(QWidget):
    """Paint a simple machine diagram and expose clickable I/O hotspots."""

    signalSelected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.profile_id = "umbrella-parasol-v1"
        self.transfer = "direct_pickup"
        self.pockets = 16
        self.signals: list[dict[str, str]] = []
        self.mapping: dict[str, dict[str, str]] = {}
        self.selected_signal = ""
        self.hotspots: dict[str, QRectF] = {}
        self.sim_pocket = 1
        self.sim_spindle_tool = 0
        self.sim_door_open = False
        self.sim_magazine_extended = False
        self.sim_drawbar_unclamped = False
        self.sim_state = "IDLE"
        self.setMinimumSize(330, 260)
        self.setToolTip("คลิกจุด I/O บนภาพเพื่อดูคำอธิบายและเลือกขา")

    def set_configuration(
        self,
        profile_id: str,
        transfer: str,
        pockets: int,
        signals: list[dict[str, str]],
        mapping: dict[str, dict[str, str]],
        selected_signal: str,
    ) -> None:
        self.profile_id = profile_id
        self.transfer = transfer
        self.pockets = pockets
        self.signals = signals
        self.mapping = mapping
        self.selected_signal = selected_signal
        self.update()

    def _draw_magazine(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#52657a"), 3))
        painter.setBrush(QColor("#dbe8f4"))
        if self.profile_id == "chain-double-arm-v1":
            path = QPainterPath()
            path.addRoundedRect(rect, 45, 45)
            painter.drawPath(path)
            painter.setBrush(QColor("#8caac4"))
            count = min(18, max(6, self.pockets))
            for index in range(count):
                portion = index / max(1, count - 1)
                x = rect.left() + 18 + portion * (rect.width() - 36)
                y = rect.top() + 18 if index % 2 == 0 else rect.bottom() - 18
                painter.drawEllipse(QPointF(x, y), 6, 6)
        elif self.profile_id == "linear-rack-v1":
            painter.drawRoundedRect(rect.adjusted(0, rect.height() * 0.35, 0, -rect.height() * 0.25), 8, 8)
            painter.setBrush(QColor("#8caac4"))
            count = min(12, max(2, self.pockets))
            for index in range(count):
                x = rect.left() + 18 + index * (rect.width() - 36) / max(1, count - 1)
                painter.drawRect(QRectF(x - 5, rect.center().y() - 7, 10, 14))
        else:
            center = rect.center()
            radius = min(rect.width(), rect.height()) * 0.43
            painter.drawEllipse(center, radius, radius)
            painter.setBrush(QColor("#8caac4"))
            count = min(16, max(4, self.pockets))
            import math
            for index in range(count):
                angle = 2 * math.pi * (index - (self.sim_pocket - 1)) / count - math.pi / 2
                point = QPointF(center.x() + radius * 0.78 * math.cos(angle), center.y() + radius * 0.78 * math.sin(angle))
                empty = index + 1 == self.sim_spindle_tool
                painter.setBrush(QColor("#ffffff") if empty else (QColor("#f4a261") if index + 1 == self.sim_pocket else QColor("#8caac4")))
                painter.drawEllipse(point, 8 if index + 1 == self.sim_pocket else 6, 8 if index + 1 == self.sim_pocket else 6)
                painter.setPen(QColor("#263746"))
                painter.setFont(QFont("Sans", 6))
                painter.drawText(QRectF(point.x()-8, point.y()-7, 16, 14), Qt.AlignCenter, str(index + 1))

        painter.setPen(QColor("#263746"))
        painter.setFont(QFont("Sans", 10, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"MAGAZINE\nTOOL {self.sim_pocket} / {self.pockets}")

    def _draw_transfer(self, painter: QPainter, center: QPointF) -> None:
        painter.setPen(QPen(QColor("#59636e"), 8, Qt.SolidLine, Qt.RoundCap))
        if self.transfer == "double_arm_180":
            painter.drawLine(QPointF(center.x() - 70, center.y()), QPointF(center.x() + 70, center.y()))
            painter.setBrush(QColor("#f4a261"))
            painter.setPen(QPen(QColor("#a6531d"), 2))
            painter.drawEllipse(QPointF(center.x() - 78, center.y()), 13, 13)
            painter.drawEllipse(QPointF(center.x() + 78, center.y()), 13, 13)
            label = "DOUBLE ARM 180°"
        elif self.transfer == "single_arm":
            painter.drawLine(center, QPointF(center.x() + 80, center.y() - 20))
            painter.setBrush(QColor("#f4a261"))
            painter.drawEllipse(QPointF(center.x() + 88, center.y() - 22), 13, 13)
            label = "SINGLE ARM"
        else:
            painter.setPen(QPen(QColor("#59636e"), 3, Qt.DashLine))
            painter.drawLine(QPointF(center.x(), center.y() - 25), QPointF(center.x(), center.y() + 25))
            label = "DIRECT PICKUP"
        painter.setPen(QColor("#263746"))
        painter.setFont(QFont("Sans", 9, QFont.Bold))
        painter.drawText(QRectF(center.x() - 95, center.y() + 15, 190, 24), Qt.AlignCenter, label)

    def _draw_spindle(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#465867"), 3))
        painter.setBrush(QColor("#d8dee4"))
        painter.drawRoundedRect(rect, 8, 8)
        painter.setBrush(QColor("#687f91"))
        painter.drawRect(QRectF(rect.center().x() - 9, rect.bottom(), 18, 25))
        painter.setPen(QColor("#263746"))
        painter.setFont(QFont("Sans", 10, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, "SPINDLE\nM19 + DRAWBAR")

    def _visible_signals(self) -> list[dict[str, str]]:
        input_priority = [
            "MAG_HOME", "MAG_INDEX", "MAG_IN_POSITION", "ARM_HOME",
            "ARM_AT_EXCHANGE", "ARM_180_POSITION", "DRAWBAR_CLAMPED",
            "TOOL_PRESENT_SPINDLE", "SPINDLE_ORIENT_IN_POSITION",
        ]
        output_priority = [
            "MAG_CW", "MAG_CCW", "ARM_EXTEND_CMD", "ARM_RETRACT_CMD",
            "ARM_ROTATE_CW", "ARM_ROTATE_CCW", "DRAWBAR_CLAMP_CMD",
            "DRAWBAR_UNCLAMP_CMD", "SPINDLE_ORIENT_CMD",
        ]
        by_id = {item["id"]: item for item in self.signals}
        inputs = [by_id[item] for item in input_priority if item in by_id]
        outputs = [by_id[item] for item in output_priority if item in by_id]
        for item in self.signals:
            target = inputs if item["direction"] == "input" else outputs
            limit = 9 if item["direction"] == "input" else 8
            if item not in target and len(target) < limit:
                target.append(item)
        return inputs[:9] + outputs[:8]

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f7fafc"))
        width, height = self.width(), self.height()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#9bd4a9") if self.sim_door_open else QColor("#9aa5ae"))
        painter.drawRoundedRect(QRectF(width * 0.15, 10, width * 0.70, 12), 5, 5)
        painter.setPen(QColor("#263746"))
        painter.setFont(QFont("Sans", 8, QFont.Bold))
        painter.drawText(QRectF(width * 0.15, 5, width * 0.70, 22), Qt.AlignCenter, "ATC DOOR OPEN" if self.sim_door_open else "ATC DOOR CLOSED")
        mag_x = width * (0.22 if self.sim_magazine_extended else 0.16)
        self._draw_magazine(painter, QRectF(mag_x, 28, width * 0.56, height * 0.32))
        self._draw_transfer(painter, QPointF(width * 0.5, height * 0.54))
        self._draw_spindle(painter, QRectF(width * 0.36, height * 0.69, width * 0.28, height * 0.17))
        painter.setPen(QColor("#b42318") if self.sim_drawbar_unclamped else QColor("#18794e"))
        painter.setFont(QFont("Sans", 9, QFont.Bold))
        painter.drawText(QRectF(width * 0.30, height * 0.88, width * 0.40, 22), Qt.AlignCenter,
                         "DRAWBAR: UNCLAMP" if self.sim_drawbar_unclamped else "DRAWBAR: CLAMPED")

        visible = self._visible_signals()
        self.hotspots = {}
        left = [item for item in visible if item["direction"] == "input"]
        right = [item for item in visible if item["direction"] == "output"]
        for side, items in (("left", left), ("right", right)):
            for index, item in enumerate(items):
                label_width = min(155, max(115, width * 0.31))
                x = 8 if side == "left" else width - label_width - 8
                y = 20 + index * min(34, max(25, (height - 45) / max(1, len(items))))
                bounds = QRectF(x, y, label_width, 25)
                self.hotspots[item["id"]] = bounds
                mapped = item["id"] in self.mapping
                disabled = item.get("disabled", False)
                selected = item["id"] == self.selected_signal
                color = QColor("#2eaf69") if mapped else QColor("#e05858")
                if disabled:
                    color = QColor("#8b949e")
                if item["requirement"] in ("optional", "recommended") and not mapped:
                    color = QColor("#e3a327")
                painter.setPen(QPen(QColor("#1f5f8b") if selected else color, 2 if selected else 1))
                painter.setBrush(QColor("#e8f4ff") if selected else QColor("#ffffff"))
                painter.drawRoundedRect(bounds, 8, 8)
                painter.setBrush(color)
                painter.drawEllipse(QPointF(bounds.left() + 10, bounds.center().y()), 5, 5)
                painter.setPen(QColor("#22313d"))
                painter.setFont(QFont("Sans", 7))
                label = _friendly_signal(item["id"])
                painter.drawText(bounds.adjusted(20, 0, -3, 0), Qt.AlignVCenter | Qt.AlignLeft, label[:25])

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        for signal_id, bounds in self.hotspots.items():
            if bounds.contains(event.pos()):
                self.signalSelected.emit(signal_id)
                return
        super().mousePressEvent(event)


class VisualAtcConfiguratorWidget(QWidget):
    """Single page visual configurator intended for a QtDragon QtVCP tab."""

    def __init__(
        self,
        data_dir: str | Path,
        config: dict[str, Any] | None = None,
        parent: QWidget | None = None,
        base_config_dir: str | Path | None = None,
        output_root: str | Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("visualAtcConfigurator")
        self.data_dir = Path(data_dir).resolve()
        self.base_config_dir = Path(base_config_dir or data_dir).expanduser().resolve()
        self.output_root = (
            Path(output_root).expanduser().resolve()
            if output_root else Path.home() / "linuxcnc" / "configs" / "universal-atc-generated"
        )
        self.manifests = _manifest_files(self.data_dir)
        if not self.manifests:
            raise FileNotFoundError("No hardware manifests found")
        manifest = self.manifests[0][1]
        if config:
            manifest_id = config.get("hardware", {}).get("manifest_id")
            manifest = next((item for _, item in self.manifests if item["manifest_id"] == manifest_id), manifest)
        self.model = WizardModel(self.data_dir, manifest, config=config)
        self.selected_signal = ""
        self._building = False
        self._last_report: dict[str, Any] | None = None
        self._sim_steps: list[str] = []
        self._sim_target = 1
        self.runtime = SimRuntime(count=self.model.config["atc"]["magazine"]["pocket_count"])
        self.monitor_window = None
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(650)
        self._sim_timer.timeout.connect(self._simulation_tick)
        self._build_ui()
        self._load_controls()
        self._refresh()

    def _build_ui(self) -> None:
        self.setStyleSheet("""
            QWidget#visualAtcConfigurator { background-color: #f2f5f7; color: #263746; }
            QWidget#visualAtcConfigurator QLabel { color: #263746; }
            QGroupBox { font-weight: 600; border: 1px solid #b8c4ce; border-radius: 6px; margin-top: 8px; padding-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QPushButton { min-height: 28px; padding: 3px 12px; }
            QComboBox, QSpinBox { min-height: 26px; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        heading = QHBoxLayout()
        title = QLabel("Universal ATC — ตั้งค่าด้วยภาพ")
        title.setStyleSheet("font-size: 17px; font-weight: 700; color: #263746;")
        self.status_chip = QLabel("พร้อมตั้งค่า")
        self.status_chip.setAlignment(Qt.AlignCenter)
        self.status_chip.setStyleSheet("background:#dceefb;color:#19577f;border-radius:10px;padding:5px 12px;")
        heading.addWidget(title, 1)
        heading.addWidget(self.status_chip)
        root.addLayout(heading)

        hint = QLabel("เลือกชนิด ATC แล้วคลิกจุดบนภาพเพื่อกำหนด Sensor และ Output — สีเขียว = กำหนดแล้ว, สีแดง = ยังขาด")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#52616d;")
        root.addWidget(hint)

        settings = QGroupBox("1. เลือกรูปแบบเครื่องจักร")
        settings.setMaximumHeight(108)
        settings_layout = QHBoxLayout(settings)
        self.manifest_combo = QComboBox()
        self.profile_combo = QComboBox()
        self.pockets_spin = QSpinBox()
        self.pockets_spin.setRange(1, 256)
        self.transfer_combo = QComboBox()
        self.feedback_combo = QComboBox()
        def add_setting(label_text: str, widget: QWidget, stretch: int = 1) -> None:
            column = QVBoxLayout()
            label = QLabel(label_text)
            label.setStyleSheet("font-size:11px;font-weight:600;")
            column.addWidget(label)
            column.addWidget(widget)
            settings_layout.addLayout(column, stretch)

        add_setting("ตัวควบคุม", self.manifest_combo, 2)
        add_setting("ชนิด ATC", self.profile_combo, 2)
        add_setting("จำนวน Pocket", self.pockets_spin)
        add_setting("กลไกเปลี่ยนทูล", self.transfer_combo, 2)
        add_setting("อ่านตำแหน่ง", self.feedback_combo, 2)
        self.machine_help = QLabel()
        self.machine_help.hide()
        root.addWidget(settings)

        content = QHBoxLayout()
        content.setSpacing(8)
        root.addLayout(content, 1)

        diagram_group = QGroupBox("2. ภาพรวม Magazine / Arm / Spindle")
        diagram_layout = QVBoxLayout(diagram_group)
        self.diagram = AtcDiagramWidget()
        self.diagram.signalSelected.connect(self._select_signal)
        diagram_layout.addWidget(self.diagram, 1)
        sim_controls = QHBoxLayout()
        self.sim_status = QLabel("การจำลอง: พร้อม — Tool 1")
        self.sim_status.setStyleSheet("background:#e7eef4;border-radius:5px;padding:5px;font-weight:600;")
        self.sim_tool = QSpinBox()
        self.sim_tool.setRange(1, 12)
        self.sim_tool.setValue(2)
        self.sim_home_button = QPushButton("Home จาน")
        self.sim_home_button.setText("รีเซ็ตการจำลอง")
        self.monitor_button = QPushButton("มอนิเตอร์ ATC / I/O")
        self.monitor_button.clicked.connect(self._open_monitor)
        self.sim_run_button = QPushButton("เปลี่ยนทูล")
        self.sim_stop_button = QPushButton("หยุด SIM")
        self.sim_run_button.setStyleSheet("background:#2374ab;color:white;font-weight:700;")
        self.sim_stop_button.setStyleSheet("background:#a33b3b;color:white;")
        sim_controls.addWidget(self.sim_status, 1)
        sim_controls.addWidget(QLabel("หมายเลข Tool เป้าหมาย:"))
        sim_controls.addWidget(self.sim_tool)
        sim_controls.addWidget(self.sim_home_button)
        sim_controls.addWidget(self.sim_run_button)
        sim_controls.addWidget(self.sim_stop_button)
        sim_controls.addWidget(self.monitor_button)
        diagram_layout.addLayout(sim_controls)
        self.sim_home_button.clicked.connect(self._simulation_home)
        self.sim_run_button.clicked.connect(self._simulation_start)
        self.sim_stop_button.clicked.connect(self._simulation_stop)
        content.addWidget(diagram_group, 1)

        io_group = QGroupBox("3. Sensor และ I/O")
        io_group.setMinimumWidth(275)
        io_group.setMaximumWidth(340)
        io_layout = QVBoxLayout(io_group)
        self.signal_list = QListWidget()
        self.signal_list.setMinimumHeight(70)
        self.signal_list.setMaximumHeight(105)
        self.signal_list.currentItemChanged.connect(self._signal_item_changed)
        io_layout.addWidget(self.signal_list, 1)
        self.signal_title = QLabel("เลือกจุดจากภาพหรือรายการ")
        self.signal_title.setStyleSheet("font-size:15px;font-weight:700;")
        self.signal_description = QLabel("ระบบจะแสดงหน้าที่ของ Sensor/Output และขาที่เชื่อมต่อ")
        self.signal_description.setWordWrap(True)
        self.signal_description.setMinimumHeight(45)
        self.signal_description.setMaximumHeight(62)
        self.signal_description.setStyleSheet("background:#fff7dc;color:#5a4300;border:1px solid #eed58a;border-radius:5px;padding:7px;")
        io_layout.addWidget(self.signal_title)
        io_layout.addWidget(self.signal_description)
        assign_form = QFormLayout()
        self.resource_combo = QComboBox()
        self.usage_combo = QComboBox()
        self.usage_combo.addItem("ใช้และตรวจสอบเซ็นเซอร์", True)
        self.usage_combo.addItem("ไม่ใช้ — ข้ามการตรวจสอบ", False)
        self.active_combo = QComboBox()
        self.active_combo.addItem("Active High — ON เมื่อมีไฟ", "high")
        self.active_combo.addItem("Active Low — ON เมื่อลงกราวด์", "low")
        assign_form.addRow("การใช้งาน:", self.usage_combo)
        assign_form.addRow("ขา I/O:", self.resource_combo)
        assign_form.addRow("ระดับสัญญาณ:", self.active_combo)
        io_layout.addLayout(assign_form)
        self.assign_button = QPushButton("กำหนดขานี้")
        self.assign_button.clicked.connect(self._assign_selected)
        io_layout.addWidget(self.assign_button)
        content.addWidget(io_group)

        actions = QHBoxLayout()
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        actions.addWidget(self.summary, 1)
        self.auto_button = QPushButton("จัดสรร I/O อัตโนมัติ")
        self.validate_button = QPushButton("ตรวจสอบ")
        self.save_button = QPushButton("บันทึกฉบับร่าง")
        self.apply_button = QPushButton("สร้าง Configuration สำหรับทดสอบ")
        self.apply_button.setStyleSheet("background:#2e8b57;color:white;font-weight:700;min-height:34px;")
        self.auto_button.clicked.connect(self._auto_map)
        self.validate_button.clicked.connect(self._validate)
        self.save_button.clicked.connect(self._save)
        self.apply_button.clicked.connect(self._apply)
        actions.addWidget(self.auto_button)
        actions.addWidget(self.validate_button)
        actions.addWidget(self.save_button)
        actions.addWidget(self.apply_button)
        root.addLayout(actions)

        self.manifest_combo.currentIndexChanged.connect(self._manifest_changed)
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        self.pockets_spin.valueChanged.connect(self._pockets_changed)
        self.transfer_combo.currentIndexChanged.connect(self._transfer_changed)
        self.feedback_combo.currentIndexChanged.connect(self._feedback_changed)

    def _set_sim_state(self, state: str, text: str) -> None:
        self.diagram.sim_state = state
        loaded = self.diagram.sim_spindle_tool
        self.sim_status.setText(f"SIM: {text} | Spindle T{loaded} | Magazine {self.diagram.pockets-int(loaded > 0)}")
        self.diagram.update()
        if self.model.manifest.get("status") == "simulated":
            try:
                import hal
                values = {
                    "carousel": self.diagram.sim_pocket - 1,
                    "magazine": float(self.diagram.sim_magazine_extended),
                    "door": float(self.diagram.sim_door_open),
                    "drawbar": float(self.diagram.sim_drawbar_unclamped),
                    "pickup": float(self.diagram.sim_drawbar_unclamped),
                    "spindle-tool": self.diagram.sim_spindle_tool,
                    "z-clear": float(self.runtime.z_clear),
                    "spindle-angle": self.runtime.spindle_angle,
                    "orient-target": self.runtime.orient_target,
                    "orient-ok": float(self.runtime.inputs.get("SPINDLE_ORIENT_IN_POSITION",False)),
                }
                for pin, value in values.items():
                    hal.set_p(f"vmcgui.{pin}", str(value))
            except (ImportError, RuntimeError):
                pass

    def _open_monitor(self) -> None:
        from .sim_monitor import SimMonitor
        if self.monitor_window is None:
            self.monitor_window = SimMonitor(self)
        self.monitor_window.show()
        self.monitor_window.raise_()

    def _sync_runtime(self) -> None:
        r = self.runtime
        self.diagram.sim_pocket = r.pocket
        self.diagram.sim_spindle_tool = r.spindle
        self.diagram.sim_door_open = r.inputs.get("ATC_DOOR_OPEN", False)
        self.diagram.sim_magazine_extended = r.inputs.get("MAGAZINE_EXTENDED", False)
        self.diagram.sim_drawbar_unclamped = r.inputs.get("DRAWBAR_UNCLAMPED", False)
        self._sim_steps = r.steps
        self.sim_run_button.setEnabled(not r.busy and r.status not in ("FAULT", "STOPPED"))
        self._set_sim_state(r.status, STEP_LABELS.get(r.status, r.status))

    def _simulation_home(self) -> None:
        self._sim_timer.stop()
        self.runtime = SimRuntime(count=self.model.config["atc"]["magazine"]["pocket_count"])
        if self.monitor_window is not None:
            self.monitor_window.fault.setCurrentIndex(0)
        self._sync_runtime()

    def _simulation_start(self) -> None:
        r = self.runtime
        r.orient_target = self.model.config["atc"]["spindle_orientation"].get("fixed_angle_deg",180)
        r.disabled = set(self.model.config["atc"].get("disabled_signals", []))
        if not r.start(self.sim_tool.value()):
            return
        self._sync_runtime()
        self._sim_timer.start()

    def _simulation_stop(self) -> None:
        self._sim_timer.stop()
        self.runtime.stop()
        self._sync_runtime()

    def _simulation_tick(self) -> None:
        self.runtime.tick(self._sim_timer.interval()/1000)
        self._sync_runtime()
        if not self.runtime.busy:
            self._sim_timer.stop()

    def _load_controls(self) -> None:
        self._building = True
        self.manifest_combo.clear()
        for _, manifest in self.manifests:
            identity = manifest.get("identity", {})
            label = f"{identity.get('controller_profile', manifest['manifest_id'])} — {manifest['status'].upper()}"
            self.manifest_combo.addItem(label, manifest["manifest_id"])
        self.manifest_combo.setCurrentIndex(max(0, self.manifest_combo.findData(self.model.manifest["manifest_id"])))
        self.profile_combo.clear()
        for profile in self.model.catalog.get("profiles", []):
            self.profile_combo.addItem(PROFILE_LABELS.get(profile["id"], profile["name_th"]), profile["id"])
        self.profile_combo.setCurrentIndex(max(0, self.profile_combo.findData(self.model.config["atc"]["profile_id"])))
        self.pockets_spin.setValue(self.model.config["atc"]["magazine"]["pocket_count"])
        self._reload_profile_options()
        self._building = False

    def _reload_profile_options(self) -> None:
        profile = self.model.profile
        atc = self.model.config["atc"]
        self.pockets_spin.setRange(profile["pocket_count"]["min"], profile["pocket_count"]["max"])
        self.transfer_combo.clear()
        for item in profile["supported_transfer_mechanisms"]:
            self.transfer_combo.addItem(TRANSFER_LABELS.get(item, item), item)
        self.transfer_combo.setCurrentIndex(max(0, self.transfer_combo.findData(atc["transfer"]["mechanism"])))
        self.feedback_combo.clear()
        for item in profile["supported_position_feedback"]:
            self.feedback_combo.addItem(FEEDBACK_LABELS.get(item, item), item)
        self.feedback_combo.setCurrentIndex(max(0, self.feedback_combo.findData(atc["magazine"]["position_feedback"]["method"])))

    def _invalidate(self) -> None:
        self._last_report = None
        self.status_chip.setText("มีการแก้ไข — กรุณาตรวจสอบ")
        self.status_chip.setStyleSheet("background:#fff0c2;color:#735800;border-radius:10px;padding:5px 12px;")

    def _manifest_changed(self, index: int) -> None:
        if self._building or index < 0:
            return
        manifest_id = self.manifest_combo.itemData(index)
        manifest = next(item for _, item in self.manifests if item["manifest_id"] == manifest_id)
        self.model.set_manifest(manifest)
        self._invalidate()
        self._refresh()

    def _profile_changed(self, index: int) -> None:
        if self._building or index < 0:
            return
        self._building = True
        self.model.set_profile(self.profile_combo.itemData(index))
        self.pockets_spin.setValue(self.model.config["atc"]["magazine"]["pocket_count"])
        self._reload_profile_options()
        self._building = False
        self._invalidate()
        self._refresh()

    def _pockets_changed(self, value: int) -> None:
        if self._building:
            return
        self.model.set_value("atc.magazine.pocket_count", value)
        self._invalidate()
        self._refresh()

    def _transfer_changed(self, index: int) -> None:
        if self._building or index < 0:
            return
        self.model.set_value("atc.transfer.mechanism", self.transfer_combo.itemData(index))
        self._invalidate()
        self._refresh()

    def _feedback_changed(self, index: int) -> None:
        if self._building or index < 0:
            return
        self.model.set_value("atc.magazine.position_feedback.method", self.feedback_combo.itemData(index))
        self._invalidate()
        self._refresh()

    def _refresh(self) -> None:
        specs = self.model.signal_specs()
        mapping = self.model.config["atc"]["io_mapping"]
        pocket_count = self.model.config["atc"]["magazine"]["pocket_count"]
        self.sim_tool.setRange(1, pocket_count)
        self.diagram.sim_pocket = min(self.diagram.sim_pocket, pocket_count)
        selected = self.selected_signal
        self.signal_list.blockSignals(True)
        self.signal_list.clear()
        selected_item = None
        for spec in specs:
            mapped = spec["id"] in mapping
            disabled = spec.get("disabled", False)
            marker = "—" if disabled else ("✓" if mapped else ("○" if spec["requirement"] in ("optional", "recommended") else "!"))
            suffix = "  (ไม่ใช้)" if disabled else ""
            item = QListWidgetItem(f"{marker}  {_friendly_signal(spec['id'])}{suffix}")
            item.setData(Qt.UserRole, spec["id"])
            item.setForeground(QColor("#8b949e") if disabled else (QColor("#24844f") if mapped else QColor("#bb3e3e")))
            self.signal_list.addItem(item)
            if spec["id"] == selected:
                selected_item = item
        self.signal_list.blockSignals(False)
        if selected_item:
            self.signal_list.setCurrentItem(selected_item)
        elif specs and not selected:
            self._select_signal(specs[0]["id"])
        active_specs = [item for item in specs if not item.get("disabled")]
        required = [item for item in active_specs if item["requirement"] in ("required", "conditional")]
        mapped_required = sum(1 for item in required if item["id"] in mapping)
        self.summary.setText(
            f"I/O ที่จำเป็น: {mapped_required}/{len(required)} Map แล้ว  |  ใช้งาน: {len(active_specs)}  ไม่ใช้: {len(specs)-len(active_specs)}"
        )
        self.machine_help.setText(
            f"ภาพนี้ใช้ Profile: {PROFILE_LABELS.get(self.model.profile['id'], self.model.profile['name_th'])}\n"
            "คลิกจุดบนภาพเพื่อดูหน้าที่ของ Sensor หรือ Output แต่ละตัว"
        )
        atc = self.model.config["atc"]
        self.diagram.set_configuration(
            atc["profile_id"], atc["transfer"]["mechanism"], atc["magazine"]["pocket_count"],
            specs, mapping, self.selected_signal,
        )

    def _signal_item_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if current:
            self._select_signal(current.data(Qt.UserRole), update_list=False)

    def _select_signal(self, signal_id: str, update_list: bool = True) -> None:
        self.selected_signal = signal_id
        spec = next((item for item in self.model.signal_specs() if item["id"] == signal_id), None)
        if spec is None:
            return
        self.signal_title.setText(_friendly_signal(signal_id))
        direction = "INPUT / SENSOR" if spec["direction"] == "input" else "OUTPUT / COMMAND"
        self.signal_description.setText(f"{direction} • {spec['requirement'].upper()}\n{_signal_help(signal_id, spec['direction'])}")
        resource_type = "digital_input" if spec["direction"] == "input" else "digital_output"
        current = self.model.config["atc"]["io_mapping"].get(signal_id, {})
        is_input = spec["direction"] == "input"
        enabled = not spec.get("disabled", False)
        self.usage_combo.setEnabled(is_input)
        self.usage_combo.setCurrentIndex(max(0, self.usage_combo.findData(enabled)))
        self.resource_combo.clear()
        self.resource_combo.addItem("— ยังไม่กำหนด —", None)
        for resource in self.model.resource_options(resource_type):
            self.resource_combo.addItem(f"{resource['id']}   {resource.get('endpoint', '')}", resource["id"])
        self.resource_combo.setCurrentIndex(max(0, self.resource_combo.findData(current.get("resource_id"))))
        self.active_combo.setCurrentIndex(max(0, self.active_combo.findData(current.get("active_level", "high"))))
        if update_list:
            for row in range(self.signal_list.count()):
                item = self.signal_list.item(row)
                if item.data(Qt.UserRole) == signal_id:
                    self.signal_list.setCurrentItem(item)
                    break
        self.diagram.selected_signal = signal_id
        self.diagram.update()

    def _assign_selected(self) -> None:
        if not self.selected_signal:
            return
        spec = next(item for item in self.model.signal_specs() if item["id"] == self.selected_signal)
        enabled = True if spec["direction"] == "output" else bool(self.usage_combo.currentData())
        self.model.set_signal_enabled(self.selected_signal, enabled)
        self.model.set_io_mapping(
            self.selected_signal,
            self.resource_combo.currentData() if enabled else None,
            self.active_combo.currentData(),
        )
        self._invalidate()
        self._refresh()
        self._select_signal(self.selected_signal)

    def _auto_map(self) -> None:
        result = self.model.auto_assign_io()
        self._invalidate()
        self._refresh()
        missing = result["unmapped_required"]
        if missing:
            QMessageBox.warning(self, "Auto-map ยังไม่ครบ", "ยังขาด I/O ที่จำเป็น:\n" + "\n".join(missing))
        else:
            QMessageBox.information(self, "Auto-map สำเร็จ", "กำหนด I/O ที่จำเป็นครบแล้ว กรุณากด ตรวจสอบ")

    def _validate(self, show_dialog: bool = True) -> dict[str, Any]:
        report = self.model.validate()
        self._last_report = report
        summary = report["summary"]
        if report["configuration_valid"]:
            self.status_chip.setText("Configuration ผ่านการตรวจสอบแล้ว")
            self.status_chip.setStyleSheet("background:#d9f3e3;color:#17633b;border-radius:10px;padding:5px 12px;")
        else:
            self.status_chip.setText("ยังมีรายการที่ต้องแก้")
            self.status_chip.setStyleSheet("background:#ffdede;color:#8d2525;border-radius:10px;padding:5px 12px;")
        message = (
            f"Valid: {'YES' if report['configuration_valid'] else 'NO'}\n"
            f"Error: {summary['error']}  Warning: {summary['warning']}  Blocker: {summary['blocker']}"
        )
        if report["findings"]:
            message += "\n\n" + "\n".join(
                f"[{item['severity'].upper()}] {item['id']}: {item['message_th']}"
                for item in report["findings"][:8]
            )
        if show_dialog:
            if report["configuration_valid"]:
                QMessageBox.information(self, "ผลการตรวจสอบ", message)
            else:
                QMessageBox.warning(self, "Configuration ยังไม่พร้อมใช้งาน", message)
        return report

    def _save(self) -> None:
        default = Path.home() / ".config" / "linuxcnc" / "universal-atc" / "atc-config.json"
        path, _ = QFileDialog.getSaveFileName(self, "บันทึก ATC Draft", str(default), "ATC JSON (*.json)")
        if path:
            saved = self.model.save(path)
            self.status_chip.setText(f"บันทึกแล้ว: {saved.name}")

    def _apply(self) -> None:
        report = self._validate(show_dialog=False)
        if not report["configuration_valid"]:
            QMessageBox.warning(self, "สร้างคอนฟิกทดสอบไม่สำเร็จ", "Configuration ยังมีข้อผิดพลาด กรุณาดูผลจากปุ่มตรวจสอบ")
            return
        if not (self.base_config_dir / "axis.ini").is_file():
            QMessageBox.warning(self, "ไม่พบ axis.ini", f"ไม่พบ axis.ini ใน\n{self.base_config_dir}")
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
        self.status_chip.setText("สร้าง Candidate สำเร็จ — พร้อมทดสอบ")
        QMessageBox.information(
            self,
            "สร้าง Configuration สำเร็จ",
            f"สร้าง LinuxCNC Candidate แล้ว:\n\n{target}\n\n"
            "ATC Enable ยังเป็น OFF และไม่มี Physical Output จนกว่าจะติดตั้ง Runtime ที่ผ่านการตรวจสอบ",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LinuxCNC Universal ATC visual configurator")
    parser.add_argument("--data-dir", default=".")
    parser.add_argument("--config")
    parser.add_argument("--base-config-dir")
    parser.add_argument("--output-root")
    args = parser.parse_args(argv)
    data_dir = Path(args.data_dir).expanduser().resolve()
    config = WizardModel.load_config(args.config) if args.config else None
    app = QApplication(sys.argv[:1])
    window = QMainWindow()
    window.setWindowTitle("LinuxCNC Universal ATC — ตั้งค่าด้วยภาพ")
    window.setCentralWidget(
        VisualAtcConfiguratorWidget(
            data_dir=data_dir,
            config=config,
            base_config_dir=args.base_config_dir or data_dir,
            output_root=args.output_root,
        )
    )
    window.resize(1450, 820)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
