"""Exercise tool inventory and live Vismach HAL pins on the simulation host."""
from pathlib import Path
import hal
from PyQt5.QtWidgets import QApplication
from atc_configurator.visual_configurator import VisualAtcConfiguratorWidget
from atc_configurator.wizard_model import WizardModel

app = QApplication([])
component = hal.component("atc_inventory_check")
component.ready()
root = Path.home() / "linuxcnc/configs/universal-atc-generated/vmc850-12-tool-sim-r001"
w = VisualAtcConfiguratorWidget(root, config=WizardModel.load_config(root / "atc_config.json"))
w._open_monitor()
app.processEvents()
assert w.monitor_window.io.rowCount() == len(w.model.signal_specs())
for target in (4, 9):
    w.sim_tool.setValue(target)
    w._simulation_start()
    w._sim_timer.stop()
    for tick in range(100):
        if not w._sim_steps:
            break
        w._simulation_tick()
    assert not w._sim_steps
    assert w.diagram.sim_spindle_tool == target
    assert int(hal.get_value("vmcgui.spindle-tool")) == target
    assert int(hal.get_value("vmcgui.carousel")) == target-1
    print(f"T{target}: spindle=1 magazine=11 empty pocket={target}; HAL synchronized")
w.diagram.sim_spindle_tool = 0
w._simulation_home()
w.close()
