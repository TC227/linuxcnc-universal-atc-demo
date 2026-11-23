"""Build an isolated QtDragon/VMC850 demo using installed LinuxCNC samples."""
import argparse
import json
import shutil
from pathlib import Path

from atc_configurator.generator import generate_candidate
from atc_configurator.wizard_model import WizardModel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-config-dir", type=Path,
                        help="Existing simulation directory containing axis.ini")
    parser.add_argument("--sample-dir", type=Path, default=Path(
        "/usr/share/doc/linuxcnc/examples/sample-configs/sim/qtdragon/qtdragon_xyz"),
        help="Installed QtDragon XYZ sample, used when --base-config-dir is omitted")
    parser.add_argument("--output-root", type=Path,
                        default=Path.home()/"linuxcnc/configs/universal-atc-generated")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output_root.expanduser().resolve()
    base = args.base_config_dir
    if base is None:
        sample = args.sample_dir.expanduser().resolve()
        if not (sample/"qtdragon_metric.ini").is_file():
            parser.error("QtDragon metric sample not found; supply --sample-dir or --base-config-dir")
        output.mkdir(parents=True, exist_ok=True)
        # Keep this reusable base: relative paths in sample INI files may refer to it.
        base = output/"qtdragon-simulation-base"
        if not base.exists():
            shutil.copytree(sample,base)
            shutil.copy2(base/"qtdragon_metric.ini",base/"axis.ini")
    print(build(root,base.expanduser(),output))


def build(root,base,output):
    config = json.loads((root/"examples/configurations/vmc-12-rotary-dc-sim.json").read_text(encoding="utf-8"))
    config["config_id"] = "vmc850-12-tool-sim"
    config["machine"]["name"] = "VMC850 12 Tool Simulation"
    manifest = json.loads((root/"examples/hardware-manifests/simulator-24di-16do.json").read_text(encoding="utf-8"))
    model = WizardModel(root,manifest,config)
    model.auto_assign_io()
    return generate_candidate(model.config,manifest,model.validate(),base,output,data_dir=root)


if __name__ == "__main__":
    main()
