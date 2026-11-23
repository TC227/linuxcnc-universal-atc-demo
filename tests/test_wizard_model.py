from copy import deepcopy
from pathlib import Path
import shutil
from xml.etree import ElementTree

from jsonschema import Draft202012Validator

from atc_configurator.io_mapper import auto_map
from atc_configurator.generator import generate_candidate
from atc_configurator.profiles import find_profile, load_profile_catalog, required_signal_specs
from atc_configurator.validator import validate_configuration
from atc_configurator.wizard_model import WizardModel, default_configuration


ROOT = Path(__file__).resolve().parents[1]
CATALOG = load_profile_catalog(ROOT / "profiles/v1/catalog.json")
SCHEMA = ROOT / "schemas/atc-config.schema.json"
MANIFEST_SCHEMA = ROOT / "schemas/hardware-manifest.schema.json"


def load_example():
    import json
    config = json.loads((ROOT / "examples/configurations/chain-24-double-arm.json").read_text())
    manifest = json.loads((ROOT / "examples/hardware-manifests/simulator-24di-16do.json").read_text())
    return config, manifest


def mapped_config(config, manifest):
    profile = find_profile(CATALOG, config["atc"]["profile_id"])
    result = auto_map(required_signal_specs(config, profile), manifest["resources"])
    assert result["unmapped_required"] == []
    config["atc"]["io_mapping"] = result["mapping"]
    return config


def validate(config, manifest):
    return validate_configuration(config, manifest, CATALOG, SCHEMA, MANIFEST_SCHEMA)


def test_default_wizard_configuration_matches_schema():
    _, manifest = load_example()
    config = default_configuration(manifest["manifest_id"])
    schema = __import__("json").loads(SCHEMA.read_text())
    Draft202012Validator(schema).validate(config)


def test_gray_code_24_pockets_requires_five_bits():
    config, _ = load_example()
    config["atc"]["magazine"]["position_feedback"] = {"method": "gray_code"}
    profile = find_profile(CATALOG, config["atc"]["profile_id"])
    specs = required_signal_specs(config, profile)
    assert len([s for s in specs if s["id"].startswith("MAG_CODE_BIT_")]) == 5


def test_bcd_24_pockets_requires_eight_bits():
    config, _ = load_example()
    config["atc"]["magazine"]["position_feedback"] = {"method": "bcd"}
    profile = find_profile(CATALOG, config["atc"]["profile_id"])
    specs = required_signal_specs(config, profile)
    assert len([s for s in specs if s["id"].startswith("MAG_BCD_BIT_")]) == 8


def test_transfer_selection_generates_double_arm_signals():
    config, _ = load_example()
    profile = find_profile(CATALOG, config["atc"]["profile_id"])
    ids = {s["id"] for s in required_signal_specs(config, profile)}
    assert {"ARM_180_POSITION", "GRIPPER_A_TOOL_PRESENT", "GRIPPER_B_TOOL_PRESENT"} <= ids


def test_pot_lift_generates_pot_feedback_and_commands():
    config, _ = load_example()
    config["atc"]["transfer"]["mechanism"] = "direct_pickup"
    config["atc"]["transfer"]["presentation"] = {"mode": "pot_lift"}
    profile = find_profile(CATALOG, config["atc"]["profile_id"])
    ids = {s["id"] for s in required_signal_specs(config, profile)}
    assert {"POT_AT_EXCHANGE", "POT_HOME", "POT_UP_CMD", "POT_DOWN_CMD"} <= ids


def test_auto_map_does_not_reuse_resources():
    config, manifest = load_example()
    profile = find_profile(CATALOG, config["atc"]["profile_id"])
    result = auto_map(required_signal_specs(config, profile), manifest["resources"])
    assigned = [item["resource_id"] for item in result["mapping"].values()]
    assert len(assigned) == len(set(assigned))
    assert result["unmapped_required"] == []


def test_auto_map_skips_reserved_resources():
    _, manifest = load_example()
    resources = deepcopy(manifest["resources"])
    resources[0]["reserved_by"] = "X Axis Home"
    result = auto_map([{"id": "TEST_INPUT", "direction": "input", "requirement": "required"}], resources)
    assert result["mapping"]["TEST_INPUT"]["resource_id"] != resources[0]["id"]


def test_valid_simulation_config_is_valid_but_not_live_applicable():
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    report = validate(config, manifest)
    assert report["configuration_valid"] is True
    assert report["live_apply_allowed"] is False
    assert report["decisions"]["enable_atc"] is False
    assert any(item["id"] == "HARDWARE_NOT_VERIFIED" for item in report["findings"])


def test_duplicate_physical_resource_is_detected():
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    keys = list(config["atc"]["io_mapping"])
    config["atc"]["io_mapping"][keys[1]]["resource_id"] = config["atc"]["io_mapping"][keys[0]]["resource_id"]
    report = validate(config, manifest)
    assert any(item["id"] == "RESOURCE_CONFLICT" for item in report["findings"])


def test_missing_required_signal_fails_validation():
    config, manifest = load_example()
    config["atc"]["io_mapping"] = {}
    report = validate(config, manifest)
    assert report["configuration_valid"] is False
    assert any(item["id"] == "REQUIRED_SIGNAL_UNMAPPED" for item in report["findings"])


def test_missing_selected_conditional_signal_fails_validation():
    config, manifest = load_example()
    config["atc"]["transfer"]["drawbar"] = {
        "type": "pneumatic", "verification_method": "sensor", "require_air_pressure": True
    }
    config = mapped_config(config, manifest)
    config["atc"]["io_mapping"].pop("AIR_PRESSURE_OK", None)
    report = validate(config, manifest)
    assert any(item["id"] == "REQUIRED_SIGNAL_UNMAPPED" and "AIR_PRESSURE_OK" in item["message_th"] for item in report["findings"])


def test_wrong_resource_type_is_detected():
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    config["atc"]["io_mapping"]["DRAWBAR_CLAMPED"]["resource_id"] = "SIM_DO00"
    report = validate(config, manifest)
    assert any(item["id"] == "RESOURCE_DIRECTION_MISMATCH" for item in report["findings"])


def test_manifest_id_mismatch_blocks_apply():
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    config["hardware"]["manifest_id"] = "some-other-board"
    report = validate(config, manifest)
    assert report["live_apply_allowed"] is False
    assert any(item["id"] == "HARDWARE_MANIFEST_ID_MISMATCH" for item in report["findings"])


def test_optional_signals_do_not_block_validation_when_unmapped():
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    config["atc"]["io_mapping"].pop("TOOL_PRESENT_SPINDLE", None)
    report = validate(config, manifest)
    assert not any(item["id"] == "REQUIRED_SIGNAL_UNMAPPED" and "TOOL_PRESENT_SPINDLE" in item["message_th"] for item in report["findings"])


def test_stale_mapping_from_previous_profile_is_detected():
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    config["atc"]["io_mapping"]["OLD_PROFILE_SENSOR"] = {"resource_id": "SIM_DI23", "active_level": "high"}
    report = validate(config, manifest)
    assert any(item["id"] == "UNKNOWN_LOGICAL_SIGNAL" for item in report["findings"])


def test_m19_backend_command_interface_mismatch_is_detected():
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    config["atc"]["spindle_orientation"]["backend"] = "linuxcnc_encoder_pid"
    report = validate(config, manifest)
    assert any(item["id"] == "M19_BACKEND_INTERFACE_MISMATCH" for item in report["findings"])


def test_verified_manifest_requires_firmware_hash_and_identity():
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    manifest["status"] = "verified"
    report = validate(config, manifest)
    assert report["live_apply_allowed"] is False
    assert any(item["id"] == "HARDWARE_IDENTITY_INCOMPLETE" for item in report["findings"])


def test_random_pocket_is_blocked_until_runtime_is_implemented():
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    config["atc"]["tool_management"]["location_model"] = "random"
    report = validate(config, manifest)
    assert any(item["id"] == "RANDOM_POCKET_RUNTIME_NOT_IMPLEMENTED" for item in report["findings"])


def test_shortest_path_requires_reversible_drive():
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    config["atc"]["magazine"]["direction_policy"] = "shortest_path"
    config["atc"]["magazine"]["reversible"] = False
    report = validate(config, manifest)
    assert any(item["id"] == "SHORTEST_PATH_REQUIRES_REVERSIBLE_DRIVE" for item in report["findings"])


def test_linear_rack_requires_pitch():
    config, manifest = load_example()
    config["atc"]["profile_id"] = "linear-rack-v1"
    config["atc"]["magazine"]["type"] = "linear_rack"
    config["atc"]["magazine"]["position_feedback"]["method"] = "home_index"
    config["atc"]["magazine"].pop("linear_pitch_mm", None)
    config["atc"]["transfer"]["mechanism"] = "direct_pickup"
    config = mapped_config(config, manifest)
    report = validate(config, manifest)
    assert any(item["id"] == "LINEAR_RACK_PITCH_REQUIRED" for item in report["findings"])


def test_wizard_model_profile_change_clears_old_io_mapping():
    _, manifest = load_example()
    model = WizardModel(ROOT, manifest)
    model.config["atc"]["io_mapping"]["OLD_SIGNAL"] = {"resource_id": "SIM_DI00", "active_level": "high"}
    model.set_profile("linear-rack-v1")
    assert model.config["atc"]["magazine"]["type"] == "linear_rack"
    assert model.config["atc"]["io_mapping"] == {}


def test_wizard_model_unset_optional_value_removes_key():
    _, manifest = load_example()
    model = WizardModel(ROOT, manifest)
    model.set_value("atc.spindle_orientation.resources.encoder_resource_id", "SIM_ENCODER0")
    model.set_value("atc.spindle_orientation.resources.encoder_resource_id", None)
    assert "encoder_resource_id" not in model.config["atc"]["spindle_orientation"]["resources"]


def test_wizard_model_saves_json_draft(tmp_path):
    _, manifest = load_example()
    model = WizardModel(ROOT, manifest)
    target = model.save(tmp_path / "draft.json")
    assert target.exists()
    assert '"schema_version": 1' in target.read_text(encoding="utf-8")


def test_auto_map_drops_old_assignment_when_resource_becomes_reserved():
    _, manifest = load_example()
    resources = deepcopy(manifest["resources"])
    signal_specs = [{"id": "MAG_HOME", "direction": "input", "requirement": "required"}]
    old = {"MAG_HOME": {"resource_id": "SIM_DI00", "active_level": "high"}}
    resources[0]["reserved_by"] = "X Axis Home"
    result = auto_map(signal_specs, resources, old)
    assert result["mapping"]["MAG_HOME"]["resource_id"] != "SIM_DI00"


def test_wizard_model_sets_numbering_direction_for_chain_profile():
    _, manifest = load_example()
    model = WizardModel(ROOT, manifest)
    model.set_profile("chain-double-arm-v1")
    assert model.config["atc"]["magazine"]["numbering_direction"] == "forward"


def test_side_mounted_chain_geometry_uses_forward_numbering():
    _, manifest = load_example()
    model = WizardModel(ROOT, manifest)
    model.set_profile("side-mounted-double-arm-v1")
    model.set_value("atc.magazine.side_mount_motion", "chain")
    assert model.config["atc"]["magazine"]["numbering_direction"] == "forward"


def test_loading_draft_does_not_silently_replace_manifest_identity():
    _, manifest = load_example()
    config = default_configuration("manifest-id-not-present")
    model = WizardModel(ROOT, manifest, config=config)
    assert model.config["hardware"]["manifest_id"] == "manifest-id-not-present"
    report = model.validate()
    assert any(item["id"] == "HARDWARE_MANIFEST_ID_MISMATCH" for item in report["findings"])


def test_generate_candidate_builds_separate_axis_configuration(tmp_path):
    config, manifest = load_example()
    config = mapped_config(config, manifest)
    report = validate(config, manifest)
    assert report["configuration_valid"] is True
    assert report["live_apply_allowed"] is False

    base = tmp_path / "axis-base"
    base.mkdir()
    original_ini = (
        "[EMC]\nMACHINE = Axis-Sim\n\n"
        "[DISPLAY]\nDISPLAY = axis\nPROGRAM_PREFIX = ../../nc_files/\n\n"
        "[HAL]\nHALFILE = core_sim.hal\n"
    )
    (base / "axis.ini").write_text(original_ini, encoding="utf-8")
    (base / "core_sim.hal").write_text("# simulator core\n", encoding="utf-8")
    # Simulate a stock LinuxCNC sim/axis folder: it has no ATC package,
    # profiles or QtVCP panel. The generator must bring those from data_dir.
    target = generate_candidate(config, manifest, report, base, data_dir=ROOT)
    generated_ini = (target / "axis.ini").read_text(encoding="utf-8")
    hal_text = (target / "atc_generated.hal").read_text(encoding="utf-8")

    assert target != base
    assert (base / "axis.ini").read_text(encoding="utf-8") == original_ini
    assert "DISPLAY = axis" in generated_ini
    assert "EMBED_TAB_NAME = Universal ATC" in generated_ini
    assert "qtvcp -d -c qtvcp_embed -x {XID} universal_atc" in generated_ini
    assert "POSTGUI_HALFILE = atc_generated.hal" in generated_ini
    assert "[ATC]" in generated_ini
    assert "POCKET_COUNT = 24" in generated_ini
    assert "ATC_ENABLE = 0" in generated_ini
    assert (target / "atc_config.json").is_file()
    assert (target / "atc_validation.json").is_file()
    assert (target / "atc_io_map.csv").is_file()
    assert (target / "README_ATC_CANDIDATE.md").is_file()
    assert (target / "qtvcp" / "panels" / "universal_atc" / "universal_atc.ui").is_file()
    assert (target / "src" / "atc_configurator" / "gui.py").is_file()
    assert (target / "profiles" / "v1" / "catalog.json").is_file()
    assert len((target / "atc_io_map.csv").read_text(encoding="utf-8-sig").splitlines()) > 1
    assert all(not line.strip() or line.lstrip().startswith("#") for line in hal_text.splitlines())

    second = generate_candidate(config, manifest, report, base, data_dir=ROOT)
    assert second != target


def test_generate_candidate_rejects_invalid_configuration(tmp_path):
    config, manifest = load_example()
    base = tmp_path / "axis-base"
    base.mkdir()
    (base / "axis.ini").write_text("[EMC]\nMACHINE = test\n", encoding="utf-8")
    report = validate(config, manifest)
    assert report["configuration_valid"] is False
    import pytest
    with pytest.raises(ValueError, match="validation errors"):
        generate_candidate(config, manifest, report, base)


def test_axis_qtvcp_panel_ui_contains_wizard_container():
    panel_ui = ROOT / "qtvcp" / "panels" / "universal_atc" / "universal_atc.ui"
    root = ElementTree.parse(panel_ui).getroot()
    names = {node.attrib.get("name") for node in root.iter("widget")}
    assert "atcWizardContainer" in names
