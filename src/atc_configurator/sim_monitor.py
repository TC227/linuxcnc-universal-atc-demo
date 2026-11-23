"""Live monitor of the simulation controller's commands and feedback."""
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QListWidget, QComboBox, QPushButton, QHeaderView)
from .sim_runtime import STEP_LABELS


class SimMonitor(QDialog):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel
        self.setWindowTitle("ATC Monitor — สถานะ I/O จำลอง")
        self.resize(1000, 650)
        root = QVBoxLayout(self)
        self.heading = QLabel()
        self.heading.setStyleSheet("font-size:16px;font-weight:bold;padding:8px;color:#18354a;background:#e5eef5")
        self.heading.setWordWrap(True)
        root.addWidget(self.heading)
        orientation = QHBoxLayout()
        self.orient_label = QLabel()
        self.orient_label.setStyleSheet("font-size:16px;padding:8px;")
        orientation.addWidget(self.orient_label,1)
        jog_spindle = QPushButton("หมุน Spindle SIM +90°")
        jog_spindle.clicked.connect(self.jog_spindle)
        m19 = QPushButton("M19 SIM → มุมอ้างอิง")
        m19.clicked.connect(self.orient_spindle)
        orientation.addWidget(jog_spindle)
        orientation.addWidget(m19)
        root.addLayout(orientation)
        bar = QHBoxLayout()
        self.target = QComboBox()
        for pocket in range(1,panel.model.config["atc"]["magazine"]["pocket_count"]+1):
            self.target.addItem(f"T{pocket}",pocket)
        run = QPushButton("เปลี่ยนทูล")
        run.clicked.connect(self.start)
        stop = QPushButton("หยุด SIM")
        stop.clicked.connect(panel._simulation_stop)
        reset = QPushButton("รีเซ็ตการจำลอง (คืนทูลทั้งหมด)")
        reset.clicked.connect(panel._simulation_home)
        self.fault = QComboBox()
        self.fault.addItem("Sensor ทำงานปกติ", "")
        for item in panel.model.signal_specs():
            if item["direction"] == "input":
                self.fault.addItem("จำลองเสีย: "+item["id"],item["id"])
        self.fault.currentIndexChanged.connect(self.set_fault)
        for widget in (self.target,run,stop,reset,self.fault):
            bar.addWidget(widget)
        root.addLayout(bar)
        columns = QHBoxLayout()
        self.sequence = QListWidget()
        self.sequence.setMaximumWidth(330)
        columns.addWidget(self.sequence)
        self.io = QTableWidget(0,5)
        self.io.setHorizontalHeaderLabels(["ประเภท","สัญญาณ Logical","ขา I/O","ค่า","สถานะ"])
        self.io.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.io.horizontalHeader().setStretchLastSection(True)
        self.io.setEditTriggers(QTableWidget.NoEditTriggers)
        columns.addWidget(self.io,1)
        root.addLayout(columns,1)
        root.addWidget(QLabel("เขียว = ON   เทา = OFF   เหลือง = รอ Feedback   แดง = Timeout   — = ไม่ใช้ Sensor\nค่าทั้งหมดมาจากตัวควบคุม SIM เดียวกับโมเดล 3D; Input เป็น Feedback จำลอง"))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(150)
        self.refresh()

    def start(self):
        self.panel.sim_tool.setValue(self.target.currentData())
        self.panel._simulation_start()

    def set_fault(self):
        self.panel.runtime.failed_sensor = self.fault.currentData()

    def jog_spindle(self):
        r = self.panel.runtime
        if r.busy or r.status in ("FAULT", "STOPPED"):
            return
        r.spindle_angle = (r.spindle_angle+90) % 360
        r.orient_settled = 0
        r.inputs["SPINDLE_ORIENT_IN_POSITION"] = False
        self.panel._sync_runtime()

    def orient_spindle(self):
        r = self.panel.runtime
        if r.busy or r.status in ("FAULT", "STOPPED"):
            return
        r.orient_target = self.panel.model.config["atc"]["spindle_orientation"].get("fixed_angle_deg",180)
        r.steps = ["ORIENT"]
        r.completed = []
        r.status = "RUNNING"
        r.elapsed = r.orient_settled = 0
        r.entered = False
        r.inputs["SPINDLE_ORIENT_IN_POSITION"] = False
        self.panel._sim_timer.start()

    def refresh(self):
        r = self.panel.runtime
        ok = r.inputs.get("SPINDLE_ORIENT_IN_POSITION",False)
        self.orient_label.setText(f"M19: {r.spindle_angle:.1f}° → {r.orient_target:.1f}° | "
            + ("● IN POSITION" if ok else "○ ยังไม่ยืนยัน"))
        self.orient_label.setStyleSheet("font-size:16px;padding:8px;background:"
            + ("#b9e6c5" if ok else "#ffe49a") + ";color:#152535")
        self.heading.setText(f"{r.status}: {STEP_LABELS.get(r.status, r.status)} | Spindle T{r.spindle} | Pocket {r.pocket} | Magazine {r.count-int(r.spindle>0)}\n"
            + (f"รอ: {r.waiting}   {r.elapsed:.1f} / 5.0 วินาที" if r.waiting else "พร้อม / ไม่มี Sensor ที่กำลังรอ")
            + (" | Z พ้นทูล" if r.z_clear else " | Z ตำแหน่งรับทูล"))
        self.sequence.clear()
        for step in r.completed:
            self.sequence.addItem("✓ "+STEP_LABELS.get(step,step))
        for index,step in enumerate(r.steps):
            self.sequence.addItem(("▶ " if index == 0 else "○ ")+STEP_LABELS.get(step,step))
        specs = self.panel.model.signal_specs()
        self.io.setRowCount(len(specs))
        mapping = self.panel.model.config["atc"]["io_mapping"]
        for row,spec in enumerate(specs):
            key = spec["id"]
            is_input = spec["direction"] == "input"
            value = bool((r.inputs if is_input else r.outputs).get(key,False))
            disabled = is_input and key in r.disabled
            waiting = is_input and key in r.waiting.split(", ")
            status = "ไม่ใช้" if disabled else ("TIMEOUT" if waiting and r.status == "FAULT" else ("รอ" if waiting else ("ON" if value else "OFF")))
            color = "#c9cdd1" if disabled else ("#ffb3b3" if status == "TIMEOUT" else ("#ffe49a" if waiting else ("#b9e6c5" if value else "#e4e7eb")))
            values = ["INPUT" if is_input else "OUTPUT",key,mapping.get(key,{}).get("resource_id","—"),"—" if disabled else str(int(value)),status]
            for col,text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setBackground(QColor(color))
                item.setForeground(QColor("#152535"))
                self.io.setItem(row,col,item)
