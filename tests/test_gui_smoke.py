import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from atc_configurator.gui import AtcWizardWidget


ROOT = Path(__file__).resolve().parents[1]
APP = QApplication.instance() or QApplication([])


def test_eight_page_wizard_builds_with_simulator_manifest():
    widget = AtcWizardWidget(ROOT)
    assert widget.page_stack.count() == 8
    assert widget.nav_list.count() == 8
    assert widget.model.manifest["status"] == "simulated"
    assert widget.apply_button.isEnabled() is False
    widget.close()
