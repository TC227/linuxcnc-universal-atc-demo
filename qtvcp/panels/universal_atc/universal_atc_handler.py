"""QtVCP handler for the Universal ATC visual panel in QtDragon or AXIS."""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout


class HandlerClass:
    def __init__(self, halcomp, widgets, paths):
        self.halcomp = halcomp
        self.w = widgets
        self.paths = paths
        self.wizard = None

    def initialized__(self):
        # Layout: <config>/qtvcp/panels/universal_atc/<panel files>
        config_root = Path(__file__).resolve().parents[3]
        source_path = str(config_root / "src")
        if source_path not in sys.path:
            sys.path.insert(0, source_path)

        container = getattr(self.w, "atcWizardContainer", None)
        if container is None:
            raise RuntimeError("QtVCP UI is missing atcWizardContainer")
        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)

        try:
            from atc_configurator.visual_configurator import VisualAtcConfiguratorWidget
            from atc_configurator.wizard_model import WizardModel

            config_path = config_root / "atc_config.json"
            if not config_path.is_file():
                config_path = config_root / "examples" / "configurations" / "chain-24-double-arm.json"
            config = WizardModel.load_config(config_path) if config_path.is_file() else None

            self.wizard = VisualAtcConfiguratorWidget(
                data_dir=config_root,
                config=config,
                base_config_dir=config_root,
                output_root=Path.home() / "linuxcnc" / "configs" / "universal-atc-generated",
                parent=container,
            )
            layout.addWidget(self.wizard)
            QTimer.singleShot(0, self._label_qtdragon_button)
            if config and config.get("hardware", {}).get("manifest_id", "").startswith("sim-"):
                QTimer.singleShot(1500, self.wizard._open_monitor)
        except Exception as exc:
            traceback.print_exc()
            message = QLabel(
                "Universal ATC panel could not start.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                "Check python3-pyqt5, python3-jsonschema and the copied source files."
            )
            message.setWordWrap(True)
            layout.addWidget(message)

    def _label_qtdragon_button(self):
        for window in QApplication.topLevelWidgets():
            button = window.findChild(QPushButton, "btn_user")
            if button is not None:
                button.setText("ATC")
                button.setToolTip("Universal ATC Configuration")
                break

    def closing_cleanup__(self):
        if self.wizard is not None:
            self.wizard.close()
            self.wizard.deleteLater()
            self.wizard = None


def get_handlers(halcomp, widgets, paths):
    return [HandlerClass(halcomp, widgets, paths)]
