"""Deterministic, simulation-only ATC sequence and I/O state."""
from dataclasses import dataclass, field


@dataclass
class SimRuntime:
    count: int = 12
    pocket: int = 1
    spindle: int = 0
    target: int = 1
    z_clear: bool = True
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    steps: list = field(default_factory=list)
    completed: list = field(default_factory=list)
    disabled: set = field(default_factory=set)
    failed_sensor: str = ""
    waiting: str = ""
    status: str = "IDLE"
    elapsed: float = 0
    entered: bool = False
    spindle_angle: float = 37.0
    orient_target: float = 180.0
    orient_settled: float = 0.0

    def __post_init__(self):
        self.inputs.update(AIR_PRESSURE_OK=True, SPINDLE_ZERO_SPEED=True,
            SPINDLE_DRIVE_READY=True, SPINDLE_DRIVE_FAULT=False,
            ATC_DOOR_CLOSED=True, ATC_DOOR_OPEN=False,
            DRAWBAR_CLAMPED=True, DRAWBAR_UNCLAMPED=False,
            MAGAZINE_RETRACTED=True, MAGAZINE_EXTENDED=False,
            SPINDLE_ORIENT_IN_POSITION=False, MAG_HOME=True,
            MAG_INDEX=False, MAG_IN_POSITION=True, TOOL_PRESENT_SPINDLE=False)

    @property
    def busy(self):
        return bool(self.steps) and self.status not in ("FAULT", "STOPPED")

    def start(self, target):
        if self.busy or self.status in ("FAULT", "STOPPED"):
            return False
        self.target = target
        self.completed = []
        self.steps = ["CHECK", "ORIENT", "Z_CLEAR", "OPEN_DOOR"]
        if self.spindle:
            self.steps += ["OLD_POCKET", "LOWER_RETURN", "EXTEND_RETURN", "UNCLAMP", "LIFT_RETURN"]
        else:
            self.steps += ["UNCLAMP"]
        self.steps += ["NEW_POCKET", "EXTEND_PICKUP", "LOWER_PICKUP", "CLAMP",
                       "RETRACT", "CLOSE_DOOR", "FINISH"]
        self.status = "RUNNING"
        self.entered = False
        self.elapsed = 0
        return True

    def stop(self):
        self.status = "STOPPED"
        self.outputs = {key: False for key in self.outputs}
        self.waiting = ""

    def tick(self, dt=.65):
        if not self.busy:
            return
        step = self.steps[0]
        self.status = step
        self.elapsed += dt
        self.outputs = {}
        expected = {}
        if step == "CHECK":
            expected = dict(AIR_PRESSURE_OK=True, SPINDLE_ZERO_SPEED=True,
                            SPINDLE_DRIVE_READY=True, SPINDLE_DRIVE_FAULT=False,
                            MAGAZINE_RETRACTED=True, ATC_DOOR_CLOSED=True)
        elif step == "ORIENT":
            self.outputs["SPINDLE_ORIENT_CMD"] = True
            delta = (self.orient_target-self.spindle_angle+180) % 360-180
            travel = 45*dt
            self.spindle_angle = (self.spindle_angle+max(-travel,min(travel,delta))) % 360
            error = abs((self.orient_target-self.spindle_angle+180) % 360-180)
            self.inputs["SPINDLE_ZERO_SPEED"] = error <= .5
            self.orient_settled = self.orient_settled+dt if error <= .5 else 0
            self.inputs["SPINDLE_ORIENT_IN_POSITION"] = (
                self.orient_settled >= .3 and self.failed_sensor != "SPINDLE_ORIENT_IN_POSITION")
            if not self.inputs["SPINDLE_ORIENT_IN_POSITION"]:
                self.waiting = "SPINDLE_ORIENT_IN_POSITION"
                if self.elapsed >= 5:
                    self.status = "FAULT"
                    self.outputs = {}
                return
            expected = {"SPINDLE_ORIENT_IN_POSITION": True}
        elif step in ("Z_CLEAR", "LIFT_RETURN", "LOWER_PICKUP", "LOWER_RETURN"):
            self.z_clear = step in ("Z_CLEAR", "LIFT_RETURN")
        elif step in ("OPEN_DOOR", "CLOSE_DOOR"):
            opened = step == "OPEN_DOOR"
            self.outputs["ATC_DOOR_OPEN_CMD" if opened else "ATC_DOOR_CLOSE_CMD"] = True
            expected = dict(ATC_DOOR_OPEN=opened, ATC_DOOR_CLOSED=not opened)
        elif step in ("EXTEND_RETURN", "EXTEND_PICKUP", "RETRACT"):
            extended = step != "RETRACT"
            self.outputs["MAGAZINE_EXTEND_CMD" if extended else "MAGAZINE_RETRACT_CMD"] = True
            expected = dict(MAGAZINE_EXTENDED=extended, MAGAZINE_RETRACTED=not extended)
        elif step in ("UNCLAMP", "CLAMP"):
            released = step == "UNCLAMP"
            self.outputs["DRAWBAR_UNCLAMP_CMD" if released else "DRAWBAR_CLAMP_CMD"] = True
            expected = dict(DRAWBAR_UNCLAMPED=released, DRAWBAR_CLAMPED=not released)
        elif step in ("OLD_POCKET", "NEW_POCKET"):
            if not self.z_clear:
                self.status = "FAULT"
                self.waiting = "Z_CLEAR"
                return
            dest = self.spindle if step == "OLD_POCKET" else self.target
            if self.pocket != dest:
                cw = (dest-self.pocket) % self.count
                ccw = (self.pocket-dest) % self.count
                direction = 1 if cw <= ccw else -1
                self.outputs["MAG_CW" if direction == 1 else "MAG_CCW"] = True
                self.pocket = (self.pocket-1+direction) % self.count+1
                self.inputs.update(MAG_HOME=self.pocket == 1, MAG_INDEX=True, MAG_IN_POSITION=False)
                self.waiting = "MAG_INDEX"
                return
            expected = {"MAG_IN_POSITION": True}
        if not self.entered:
            self.entered = True
            self.waiting = ", ".join(expected)
            return
        # Simulated feedback follows commands one tick later. Fault injection
        # prevents selected feedback reaching the requested state.
        for sensor, value in expected.items():
            if step not in ("CHECK", "ORIENT"):
                self.inputs[sensor] = not value if sensor == self.failed_sensor else value
        missing = [s for s,v in expected.items() if s not in self.disabled
                   and (self.inputs.get(s) != v or s == self.failed_sensor)]
        self.waiting = ", ".join(missing)
        if missing:
            if self.elapsed >= 5:
                self.status = "FAULT"
                self.outputs = {}
            return
        if step == "LIFT_RETURN":
            self.spindle = 0
        elif step == "CLAMP":
            self.spindle = self.target
        self.inputs["TOOL_PRESENT_SPINDLE"] = self.spindle > 0
        self.inputs["MAG_INDEX"] = False
        self.completed.append(self.steps.pop(0))
        self.entered = False
        self.elapsed = 0
        if not self.steps:
            self.status = "COMPLETE"
            self.outputs = {}


STEP_LABELS = {
    "CHECK": "ตรวจ Interlock", "ORIENT": "จัดแนว Spindle M19",
    "Z_CLEAR": "ยกหัว Z ให้พ้นทูล", "OPEN_DOOR": "เปิดประตู ATC",
    "OLD_POCKET": "หมุนหาช่องของทูลเดิม", "EXTEND_RETURN": "เลื่อนก้ามรับทูลเดิม",
    "LOWER_RETURN": "ลดหัวถึงระดับคืนทูลเดิม",
    "UNCLAMP": "ปลด Drawbar", "LIFT_RETURN": "ยกหัวออกจากทูลเดิม",
    "NEW_POCKET": "หมุนหาทูลใหม่", "EXTEND_PICKUP": "Magazine ตำแหน่งรับทูล",
    "LOWER_PICKUP": "ลดหัวสวมทูลใหม่", "CLAMP": "จับ Drawbar",
    "RETRACT": "ถอย Magazine", "CLOSE_DOOR": "ปิดประตู ATC", "FINISH": "จบการเปลี่ยนทูล",
}
