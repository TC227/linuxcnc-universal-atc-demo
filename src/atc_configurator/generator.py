"""Generate an isolated LinuxCNC AXIS or QtDragon candidate from an ATC draft.

The generator never edits the source machine configuration. It copies a known
simulation configuration to a new directory and adds ATC metadata. The supported
QtDragon VMC850 simulation also loads a Vismach display using simulation pins.
No physical hardware wiring is generated.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path
from typing import Any

from .profiles import find_profile, required_signal_specs


AXIS_EMBED_COMMAND = (
    "halcmd loadusr -Wn qtvcp_embed qtvcp -d -c qtvcp_embed "
    "-x {XID} universal_atc"
)


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-_")
    return slug[:48] or "atc-config"


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {
        "generated", ".git", ".venv", "__pycache__", ".pytest_cache",
        "build", "dist",
        ".venv-test",
    }
    return {
        name for name in names
        if name in ignored or name.endswith((".pyc", ".pyo"))
    }


def _section_bounds(lines: list[str], section: str) -> tuple[int, int] | None:
    pattern = re.compile(rf"^\s*\[{re.escape(section)}\]\s*$", re.IGNORECASE)
    start = next((i for i, line in enumerate(lines) if pattern.match(line)), None)
    if start is None:
        return None
    end = next(
        (i for i in range(start + 1, len(lines)) if re.match(r"^\s*\[.+\]\s*$", lines[i])),
        len(lines),
    )
    return start, end


def _set_ini_key(text: str, section: str, key: str, value: str) -> str:
    lines = text.splitlines()
    bounds = _section_bounds(lines, section)
    if bounds is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([f"[{section}]", f"{key} = {value}"])
        return "\n".join(lines) + "\n"

    start, end = bounds
    key_pattern = re.compile(rf"^\s*{re.escape(key)}\s*=", re.IGNORECASE)
    matches = [i for i in range(start + 1, end) if key_pattern.match(lines[i])]
    replacement = f"{key} = {value}"
    if matches:
        lines[matches[0]] = replacement
        for index in reversed(matches[1:]):
            del lines[index]
    else:
        lines.insert(start + 1, replacement)
    return "\n".join(lines) + "\n"


def _replace_ini_section(text: str, section: str, entries: list[tuple[str, str]]) -> str:
    lines = text.splitlines()
    bounds = _section_bounds(lines, section)
    if bounds is not None:
        start, end = bounds
        del lines[start:end]
    while lines and not lines[-1].strip():
        lines.pop()
    if lines:
        lines.append("")
    lines.append(f"[{section}]")
    lines.extend(f"{key} = {value}" for key, value in entries)
    return "\n".join(lines) + "\n"


def _atc_ini_entries(config: dict[str, Any], manifest: dict[str, Any]) -> list[tuple[str, str]]:
    atc = config["atc"]
    magazine = atc["magazine"]
    transfer = atc["transfer"]
    spindle = atc["spindle_orientation"]
    feedback = magazine["position_feedback"]
    drawbar = transfer.get("drawbar", {})
    entries = [
        ("CONFIG_ID", config["config_id"]),
        ("CONFIG_REVISION", str(config.get("revision", 1))),
        ("CANDIDATE_ONLY", "1"),
        ("ATC_ENABLE", "0"),
        ("HARDWARE_MANIFEST_ID", manifest["manifest_id"]),
        ("HARDWARE_STATUS", manifest["status"].upper()),
        ("PROFILE_ID", atc["profile_id"]),
        ("MAGAZINE_TYPE", magazine["type"]),
        ("POCKET_COUNT", str(magazine["pocket_count"])),
        ("REFERENCE_POCKET", str(magazine.get("reference_pocket", 1))),
        ("NUMBERING_DIRECTION", magazine.get("numbering_direction", "")),
        ("DIRECTION_POLICY", magazine.get("direction_policy", "one_way")),
        ("DRIVE_TYPE", magazine["drive"]["type"]),
        ("DRIVE_INTERFACE", magazine["drive"]["interface"]),
        ("POSITION_FEEDBACK", feedback["method"]),
        ("TRANSFER_MECHANISM", transfer["mechanism"]),
        ("PRESENTATION_MODE", transfer.get("presentation", {}).get("mode", "fixed")),
        ("DRAWBAR_TYPE", drawbar.get("type", "not_configured")),
        ("DRAWBAR_VERIFICATION", drawbar.get("verification_method", "not_configured")),
        ("TOOL_LOCATION_MODEL", atc["tool_management"]["location_model"]),
        ("M19_BACKEND", spindle["backend"]),
        ("M19_COMMAND_INTERFACE", spindle["command_interface"]),
        ("M19_TARGET_MODE", spindle["target_mode"]),
        ("M19_FIXED_ANGLE_DEG", str(spindle.get("fixed_angle_deg", ""))),
        ("M19_OFFSET_DEG", str(spindle.get("orientation_offset_deg", 0))),
        ("M19_TOLERANCE_DEG", str(spindle.get("tolerance_deg", ""))),
        ("M19_TIMEOUT_MS", str(spindle.get("timeout_ms", ""))),
        ("LIVE_APPLY_ALLOWED", "0"),
    ]
    for signal_id, mapped in sorted(atc.get("io_mapping", {}).items()):
        resource = next(
            (item for item in manifest["resources"] if item["id"] == mapped["resource_id"]),
            {},
        )
        entries.extend([
            (f"IO_{signal_id}_RESOURCE", mapped["resource_id"]),
            (f"IO_{signal_id}_ACTIVE_LEVEL", mapped["active_level"]),
            (f"IO_{signal_id}_ENDPOINT", resource.get("endpoint", "unknown")),
        ])
    return entries


def generate_candidate(
    config: dict[str, Any],
    manifest: dict[str, Any],
    report: dict[str, Any],
    base_config_dir: str | Path,
    output_root: str | Path | None = None,
    data_dir: str | Path | None = None,
) -> Path:
    """Create a separate, runnable Axis simulation config containing ATC data."""
    base = Path(base_config_dir).expanduser().resolve()
    data_root = Path(data_dir).expanduser().resolve() if data_dir else base
    source_ini = base / "axis.ini"
    if not source_ini.is_file():
        raise FileNotFoundError(f"Axis simulation base config not found: {source_ini}")
    if not report.get("configuration_valid"):
        raise ValueError("Configuration has validation errors; candidate generation is blocked.")
    if report.get("config_id") != config.get("config_id"):
        raise ValueError("Validation report does not match the current configuration.")
    if config.get("hardware", {}).get("manifest_id") != manifest.get("manifest_id"):
        raise ValueError("Configuration and Hardware Manifest identities do not match.")

    root = Path(output_root).expanduser().resolve() if output_root else base / "generated"
    root.mkdir(parents=True, exist_ok=True)
    stem = f"{_safe_slug(config.get('config_id', 'atc-config'))}-r{int(config.get('revision', 1)):03d}"
    target = root / stem
    suffix = 2
    while target.exists():
        target = root / f"{stem}-{suffix:02d}"
        suffix += 1

    shutil.copytree(base, target, ignore=_copy_ignore)

    # A stock LinuxCNC sim/axis directory does not contain the ATC package.
    # Bring the panel and its runtime/data into the isolated candidate so the
    # embedded tab still works when the source base is the system AXIS sample.
    for directory in ("src", "schemas", "profiles", "examples"):
        source = data_root / directory
        if source.is_dir():
            shutil.copytree(source, target / directory, dirs_exist_ok=True)
    panel_source = data_root / "qtvcp" / "panels" / "universal_atc"
    if panel_source.is_dir():
        shutil.copytree(
            panel_source,
            target / "qtvcp" / "panels" / "universal_atc",
            dirs_exist_ok=True,
        )

    ini_path = target / "axis.ini"
    if not ini_path.is_file():
        raise FileNotFoundError(f"Copied Axis INI not found: {ini_path}")

    ini_text = ini_path.read_text(encoding="utf-8")
    ini_text = _set_ini_key(ini_text, "EMC", "MACHINE", config.get("machine", {}).get("name") or "LinuxCNC-Universal-ATC-Candidate")
    ini_text = _set_ini_key(ini_text, "DISPLAY", "EMBED_TAB_NAME", "Universal ATC")
    ini_text = _set_ini_key(ini_text, "DISPLAY", "EMBED_TAB_COMMAND", AXIS_EMBED_COMMAND)
    is_qtdragon = bool(re.search(r"^\s*DISPLAY\s*=\s*qtvcp\s+qtdragon\s*$", ini_text, re.IGNORECASE | re.MULTILINE))
    if is_qtdragon:
        ini_text = _set_ini_key(ini_text, "DISPLAY", "EMBED_TAB_COMMAND", "qtvcp universal_atc")
        ini_text = _set_ini_key(ini_text, "DISPLAY", "EMBED_TAB_LOCATION", "stackedWidget_mainTab")

    # Keep relative program paths pointing at the same NC file directory after
    # moving the config one level deeper into its generated/ subdirectory.
    display_bounds = _section_bounds(ini_text.splitlines(), "DISPLAY")
    if display_bounds:
        display_lines = ini_text.splitlines()
        start, end = display_bounds
        prefix_line = next(
            (display_lines[i] for i in range(start + 1, end)
             if re.match(r"^\s*PROGRAM_PREFIX\s*=", display_lines[i], re.IGNORECASE)),
            None,
        )
        if prefix_line:
            raw_prefix = prefix_line.split("=", 1)[1].strip()
            prefix_path = Path(raw_prefix).expanduser()
            if not prefix_path.is_absolute():
                prefix_path = (base / prefix_path).resolve()
            ini_text = _set_ini_key(ini_text, "DISPLAY", "PROGRAM_PREFIX", str(prefix_path) + "/")

    ini_text = _set_ini_key(ini_text, "HAL", "POSTGUI_HALFILE", "atc_generated.hal")
    ini_text = _replace_ini_section(ini_text, "ATC", _atc_ini_entries(config, manifest))
    ini_path.write_text(ini_text, encoding="utf-8")

    catalog_path = data_root / "profiles" / "v1" / "catalog.json"
    profile = None
    if catalog_path.is_file():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        profile = find_profile(catalog, config["atc"]["profile_id"])
    specs = required_signal_specs(config, profile) if profile else []
    resource_by_id = {item["id"]: item for item in manifest["resources"]}

    (target / "atc_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (target / "atc_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with (target / "atc_io_map.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["logical_signal", "requirement", "direction", "resource_id", "endpoint", "active_level"])
        for spec in specs:
            mapped = config["atc"].get("io_mapping", {}).get(spec["id"], {})
            resource = resource_by_id.get(mapped.get("resource_id"), {})
            writer.writerow([
                spec["id"], spec["requirement"], spec["direction"],
                mapped.get("resource_id", ""), resource.get("endpoint", ""),
                mapped.get("active_level", ""),
            ])

    hal_lines = [
        "# LinuxCNC Universal ATC - generated candidate HAL file",
        "# This file is intentionally inert: it contains comments only.",
        "# No physical output, motion command, net, setp, loadrt or loadusr is emitted.",
        "# The ATC runtime component and verified hardware pin contract are not implemented yet.",
        f"# Config ID: {config['config_id']}",
        f"# Hardware: {manifest['identity']['controller_profile']} ({manifest['status']})",
    ]
    for signal_id, mapped in sorted(config["atc"].get("io_mapping", {}).items()):
        resource = resource_by_id.get(mapped["resource_id"], {})
        hal_lines.append(
            f"# MAP {signal_id} -> {mapped['resource_id']} "
            f"({resource.get('endpoint', 'unknown')}), active={mapped['active_level']}"
        )
    vismach_files = []
    if (is_qtdragon and manifest.get("status") == "simulated"
            and config["atc"].get("profile_id") == "rotary-disc-v1"
            and config["atc"]["magazine"]["pocket_count"] == 12
            and config["atc"]["transfer"]["mechanism"] == "direct_pickup"):
        vismach_source = data_root / "scripts" / "vmc850_vismach.py"
        if vismach_source.is_file():
            (target / "vismach_vmc").mkdir(exist_ok=True)
            shutil.copy2(vismach_source, target / "vismach_vmc" / "vmcgui")
            (target / "scripts").mkdir(exist_ok=True)
            shutil.copy2(vismach_source, target / "scripts" / "vmc850_vismach.py")
            launcher = target / "vmcgui_launcher"
            launcher.write_text(
                '#!/bin/bash\ncd "$(dirname "$0")/vismach_vmc" || exit 1\nexec /usr/bin/python3 ./vmcgui\n',
                encoding="utf-8",
            )
            launcher.chmod(0o755)
            (target / "atc_vismach.hal").write_text(
                "# Vismach VMC 3D model for this isolated simulation candidate.\n"
                "loadusr -Wn vmcgui ./vmcgui_launcher\n"
                "net Xpos => vmcgui.X\n"
                "net Ypos => vmcgui.Y\n"
                "net Zpos => vmcgui.Z\n"
                "setp vmcgui.magazine 0\n"
                "setp vmcgui.carousel 0\n"
                "setp vmcgui.door 0\n"
                "setp vmcgui.drawbar 0\n"
                "setp vmcgui.pickup 0\n",
                encoding="utf-8",
            )
            hal_lines.extend(["", "# Load the VMC 3D simulation window.", "source atc_vismach.hal"])
            hal_lines[1:4] = ["# Loads the simulation-only Vismach display; no physical I/O wiring."]
            vismach_files = ["atc_vismach.hal", "vmcgui_launcher", "vismach_vmc/vmcgui", "scripts/vmc850_vismach.py"]
    (target / "atc_generated.hal").write_text("\n".join(hal_lines) + "\n", encoding="utf-8")

    readme = [
        "# Universal ATC - Generated LinuxCNC Candidate",
        "",
        f"- Configuration: {config['config_id']} revision {config.get('revision', 1)}",
        f"- Hardware Manifest: {manifest['manifest_id']} ({manifest['status'].upper()})",
        f"- ATC Profile: {config['atc']['profile_id']}",
        "- Candidate type: isolated LinuxCNC simulation configuration",
        f"- VMC850 Vismach: {'included' if vismach_files else 'not included'}",
        "- ATC Enable: DISABLED",
        "- Live Apply: NOT IMPLEMENTED",
        "",
        "## Run",
        "",
        "    linuxcnc axis.ini",
        "",
        "## Safety boundary",
        "",
        "This is a separate copy of the Axis simulation configuration. It does not",
        "modify the source configuration. atc_generated.hal is loaded as a",
        "POSTGUI_HALFILE. For the supported QtDragon 12-tool simulation it loads",
        "Vismach and connects simulated XYZ signals; otherwise it is comment-only.",
        "The visual panel provides simulation I/O and animation, not real M6/M19",
        "execution or production ATC control. Do not use this candidate",
        "to operate real ATC hardware.",
        "",
        "Generated files: atc_config.json, atc_validation.json,",
        "atc_io_map.csv, and atc_generated.hal.",
    ]
    (target / "README_ATC_CANDIDATE.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

    (target / "atc_apply_manifest.json").write_text(
        json.dumps({
            "generation_version": 1,
            "config_id": config["config_id"],
            "revision": config.get("revision", 1),
            "hardware_manifest_id": manifest["manifest_id"],
            "hardware_status": manifest["status"],
            "candidate_only": True,
            "live_apply_allowed": False,
            "atc_enable": False,
            "files": [
                "axis.ini", "atc_config.json", "atc_validation.json",
                "atc_io_map.csv", "atc_generated.hal", "README_ATC_CANDIDATE.md",
            ] + vismach_files,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target
