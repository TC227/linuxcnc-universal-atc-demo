from pathlib import Path

from atc_configurator.io_mapper import auto_map
from atc_configurator.profiles import find_profile, load_profile_catalog, required_signal_specs
from atc_configurator.validator import validate_configuration


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
    specs = required_signal_specs(config, profile)
    result = auto_map(specs, manifest["resources"])
    assert result["unmapped_required"] == []
    config["atc"]["io_mapping"] = result["mapping"]
    return config


def validate(config, manifest):
    return validate_configuration(config, manifest, CATALOG, SCHEMA, MANIFEST_SCHEMA)


def test_gray_code_24_pockets_requires_five_bits():
    config, _ = load_example()
    config["atc"]["magazine"]["position_feedback"] = {"method": "gray_code"}
    profile = find_profile(CATALOG, config["atc"]["profile_id"])
    specs = required_signal_specs(config, profile)
    code_bits = [s for s in specs if s["id"].startswith("MAG_CODE_BIT_")]
    assert len(code_bits) == 5


def test_auto_map_does_not_reuse_resources():
    config, manifest = load_example()
    profile = find_profile(CATALOG, config["atc"]["profile_id"])
    specs = required_signal_specs(config, profile)
    result = auto_map(specs, manifest["resources"])
    assigned = [item["resource_id"] for item in result["mapping"].values()]
    assert len(assigned) == len(set(assigned))
    assert result["unmapped_required"] == []


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
