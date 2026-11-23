"""Check that the published VMC demo can be rebuilt and applied again."""
import json
from pathlib import Path

from atc_configurator.generator import generate_candidate
from atc_configurator.wizard_model import WizardModel

ROOT = Path(__file__).resolve().parents[1]


def vmc_model():
    config = json.loads((ROOT/"examples/configurations/vmc-12-rotary-dc-sim.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT/"examples/hardware-manifests/simulator-24di-16do.json").read_text(encoding="utf-8"))
    model = WizardModel(ROOT,manifest,config)
    model.auto_assign_io()
    return model


def test_vmc_sensor_can_be_disabled_and_reenabled():
    model = vmc_model()
    model.set_signal_enabled("ATC_DOOR_OPEN",False)
    model.auto_assign_io()
    assert "ATC_DOOR_OPEN" not in model.config["atc"]["io_mapping"]
    assert model.validate()["configuration_valid"]
    model.set_signal_enabled("ATC_DOOR_OPEN",True)
    assert not model.validate()["configuration_valid"]
    model.auto_assign_io()
    assert model.validate()["configuration_valid"]


def test_qtdragon_candidate_retains_model_for_second_apply(tmp_path):
    model = vmc_model()
    base = tmp_path/"base"
    base.mkdir()
    (base/"axis.ini").write_text("[DISPLAY]\nDISPLAY = qtvcp qtdragon\n[HAL]\nHALFILE = sim.hal\n",encoding="utf-8")
    target = generate_candidate(model.config,model.manifest,model.validate(),base,tmp_path/"out",ROOT)
    ini = (target/"axis.ini").read_text(encoding="utf-8")
    assert "EMBED_TAB_LOCATION = stackedWidget_mainTab" in ini
    assert "EMBED_TAB_COMMAND = qtvcp universal_atc" in ini
    assert "source atc_vismach.hal" in (target/"atc_generated.hal").read_text()
    assert (target/"scripts/vmc850_vismach.py").is_file()
    manifest = json.loads((target/"atc_apply_manifest.json").read_text())
    assert "vismach_vmc/vmcgui" in manifest["files"]
    second = generate_candidate(model.config,model.manifest,model.validate(),target,tmp_path/"out",target)
    assert (second/"vismach_vmc/vmcgui").read_bytes() == (ROOT/"scripts/vmc850_vismach.py").read_bytes()
    assert "source atc_vismach.hal" in (second/"atc_generated.hal").read_text()


def test_axis_base_keeps_comment_only_hal(tmp_path):
    model = vmc_model()
    base = tmp_path/"base"
    base.mkdir()
    (base/"axis.ini").write_text("[DISPLAY]\nDISPLAY = axis\n",encoding="utf-8")
    target = generate_candidate(model.config,model.manifest,model.validate(),base,tmp_path/"out",ROOT)
    assert all(not line.strip() or line.startswith("#")
               for line in (target/"atc_generated.hal").read_text().splitlines())
