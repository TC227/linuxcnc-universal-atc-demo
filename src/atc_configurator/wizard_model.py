"""Shared eight-page wizard model. No Qt or LinuxCNC runtime dependency."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .io_mapper import auto_map
from .profiles import find_profile, required_signal_specs
from .validator import validate_configuration


def default_configuration(manifest_id: str, linuxcnc_version: str = "2.9") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "config_id": "new-atc-configuration",
        "revision": 1,
        "machine": {"name": "", "linuxcnc_version": linuxcnc_version},
        "hardware": {"manifest_id": manifest_id},
        "atc": {
            "profile_id": "umbrella-parasol-v1",
            "disabled_signals": [],
            "magazine": {
                "type": "umbrella",
                "pocket_count": 16,
                "reference_pocket": 1,
                "numbering_direction": "cw",
                "direction_policy": "one_way",
                "reversible": False,
                "drive": {"type": "stepper", "interface": "stepgen"},
                "position_feedback": {
                    "method": "gray_code",
                    "bit_order": "lsb_first",
                    "has_valid_strobe": False,
                    "stable_sample_ms": 50,
                },
            },
            "transfer": {
                "mechanism": "direct_pickup",
                "presentation": {"mode": "fixed"},
                "drawbar": {
                    "type": "pneumatic",
                    "verification_method": "sensor",
                    "require_air_pressure": True,
                },
            },
            "tool_management": {"location_model": "fixed"},
            "io_mapping": {},
            "motion_resources": {},
            "spindle_orientation": {
                "backend": "linuxcnc_encoder_pid",
                "command_interface": "linuxcnc_m19",
                "target_mode": "fixed",
                "fixed_angle_deg": 180.0,
                "orientation_offset_deg": 0.0,
                "direction_policy": "shortest",
                "tolerance_deg": 1.0,
                "settling_ms": 200,
                "timeout_ms": 8000,
                "require_zero_speed": True,
                "require_brake_feedback": False,
                "resources": {},
            },
            "timeouts_ms": {
                "magazine_home": 15000,
                "magazine_index": 10000,
                "spindle_orient": 8000,
                "tool_exchange": 12000,
                "drawbar": 3000,
                "arm": 5000,
            },
            "sequence_options": {
                "require_spindle_stop": True,
                "require_m19": True,
                "require_air_pressure": True,
                "require_tool_present": False,
                "use_atc_door": False,
                "max_retries": 0,
            },
        },
    }


def set_path(data: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    node = data
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def get_path(data: dict[str, Any], dotted_path: str, default: Any = None) -> Any:
    node: Any = data
    for part in dotted_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


class WizardModel:
    """One source of truth for every page of the ATC Setup Wizard."""

    def __init__(
        self,
        data_dir: str | Path,
        manifest: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.manifest = deepcopy(manifest)
        self.catalog_path = self.data_dir / "profiles" / "v1" / "catalog.json"
        self.config_schema_path = self.data_dir / "schemas" / "atc-config.schema.json"
        self.manifest_schema_path = self.data_dir / "schemas" / "hardware-manifest.schema.json"
        with self.catalog_path.open("r", encoding="utf-8") as stream:
            self.catalog = json.load(stream)
        self.config = deepcopy(config) if config else default_configuration(self.manifest["manifest_id"])
        if config is None:
            self.config["hardware"]["manifest_id"] = self.manifest["manifest_id"]

    @property
    def profile(self) -> dict[str, Any]:
        profile = find_profile(self.catalog, self.config["atc"]["profile_id"])
        if profile is None:
            raise ValueError(f"Unknown ATC profile: {self.config['atc']['profile_id']}")
        return profile

    def set_manifest(self, manifest: dict[str, Any]) -> None:
        self.manifest = deepcopy(manifest)
        self.config["hardware"]["manifest_id"] = manifest["manifest_id"]
        self.config["atc"]["io_mapping"] = {}
        self.config["atc"]["motion_resources"] = {}
        self.config["atc"]["spindle_orientation"]["resources"] = {}

    def set_profile(self, profile_id: str) -> None:
        profile = find_profile(self.catalog, profile_id)
        if profile is None:
            raise ValueError(f"Unknown ATC profile: {profile_id}")
        atc = self.config["atc"]
        atc["profile_id"] = profile_id
        atc["magazine"]["type"] = profile["magazine_type"]
        atc["magazine"]["pocket_count"] = max(
            profile["pocket_count"]["min"],
            min(atc["magazine"]["pocket_count"], profile["pocket_count"]["max"]),
        )
        if atc["magazine"]["position_feedback"]["method"] not in profile["supported_position_feedback"]:
            atc["magazine"]["position_feedback"]["method"] = profile["supported_position_feedback"][0]
        numbering = atc["magazine"].get("numbering_direction")
        if profile["magazine_type"] in ("chain",):
            allowed_numbering = ("forward", "reverse")
            default_numbering = "forward"
        elif profile["magazine_type"] == "linear_rack":
            allowed_numbering = ("positive", "negative")
            default_numbering = "positive"
        else:
            allowed_numbering = ("cw", "ccw")
            default_numbering = "cw"
        if numbering not in allowed_numbering:
            atc["magazine"]["numbering_direction"] = default_numbering
        if atc["transfer"]["mechanism"] not in profile["supported_transfer_mechanisms"]:
            atc["transfer"]["mechanism"] = profile["supported_transfer_mechanisms"][0]
        atc["io_mapping"] = {}
        atc["motion_resources"] = {}

    def set_value(self, dotted_path: str, value: Any) -> None:
        if value is None:
            parts = dotted_path.split(".")
            node = self.config
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node.pop(parts[-1], None)
        else:
            set_path(self.config, dotted_path, value)
        if dotted_path == "atc.magazine.side_mount_motion":
            direction = self.config["atc"]["magazine"].get("numbering_direction")
            allowed = ("forward", "reverse") if value == "chain" else ("cw", "ccw")
            if direction not in allowed:
                self.config["atc"]["magazine"]["numbering_direction"] = allowed[0]
        if dotted_path.startswith(("atc.magazine.", "atc.transfer.", "atc.spindle_orientation.")):
            self.config["atc"]["io_mapping"] = {}

    def signal_specs(self) -> list[dict[str, str]]:
        return required_signal_specs(self.config, self.profile)

    def auto_assign_io(self) -> dict[str, Any]:
        result = auto_map(
            [item for item in self.signal_specs() if not item.get("disabled")],
            self.manifest.get("resources", []),
            self.config["atc"].get("io_mapping", {}),
        )
        self.config["atc"]["io_mapping"] = result["mapping"]
        return result

    def set_signal_enabled(self, signal_id: str, enabled: bool) -> None:
        disabled = self.config["atc"].setdefault("disabled_signals", [])
        if enabled:
            disabled[:] = [item for item in disabled if item != signal_id]
        elif signal_id not in disabled:
            disabled.append(signal_id)
            self.config["atc"].get("io_mapping", {}).pop(signal_id, None)

    def set_io_mapping(self, signal_id: str, resource_id: str | None, active_level: str = "high") -> None:
        mapping = self.config["atc"]["io_mapping"]
        if not resource_id:
            mapping.pop(signal_id, None)
            return
        mapping[signal_id] = {"resource_id": resource_id, "active_level": active_level}

    def resource_options(self, resource_type: str) -> list[dict[str, Any]]:
        return [
            resource for resource in self.manifest.get("resources", [])
            if resource.get("type") == resource_type
            and resource.get("available") is True
            and resource.get("verified") is True
            and not resource.get("reserved_by")
            and resource.get("status", "available") == "available"
        ]

    def validate(self) -> dict[str, Any]:
        return validate_configuration(
            self.config,
            self.manifest,
            self.catalog,
            self.config_schema_path,
            self.manifest_schema_path,
        )

    def save(self, path: str | Path) -> Path:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    @classmethod
    def load_config(cls, path: str | Path) -> dict[str, Any]:
        with Path(path).expanduser().open("r", encoding="utf-8") as stream:
            return json.load(stream)
