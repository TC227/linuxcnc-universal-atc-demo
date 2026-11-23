"""Command-line entry point for offline ATC configuration checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .profiles import load_profile_catalog
from .validator import validate_configuration


def main() -> int:
    parser = argparse.ArgumentParser(prog="atc-config", description="Validate a LinuxCNC Universal ATC configuration.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="Validate a configuration against a hardware manifest.")
    validate.add_argument("--config", required=True)
    validate.add_argument("--manifest", required=True)
    validate.add_argument("--profiles", default="profiles/v1/catalog.json")
    validate.add_argument("--config-schema", default="schemas/atc-config.schema.json")
    validate.add_argument("--manifest-schema", default="schemas/hardware-manifest.schema.json")
    validate.add_argument("--output")

    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    catalog = load_profile_catalog(args.profiles)
    report = validate_configuration(config, manifest, catalog, args.config_schema, args.manifest_schema)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["configuration_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
