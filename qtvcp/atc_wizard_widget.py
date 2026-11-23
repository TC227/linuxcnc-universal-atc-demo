"""QtVCP integration import shim.

A custom QtVCP handler can embed AtcWizardWidget inside a QWidget container.
The widget is configuration-only and does not access HAL or machine outputs.
"""

from atc_configurator.gui import AtcWizardWidget

__all__ = ["AtcWizardWidget"]
