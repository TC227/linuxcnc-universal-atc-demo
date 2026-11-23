# LinuxCNC Universal ATC — Demo

A public, curated demonstration of the LinuxCNC Universal ATC configurator and VMC850 simulation.

This repository contains selected source files and examples only. It is intentionally separate from the development repository: no private Git history, branches, pull requests, hardware-design documents, or board pin maps are copied here.

## What is included

- Eight-page ATC configuration wizard (Qt / PyQt5)
- ATC profiles, configuration schemas, validation and deterministic I/O auto-mapping
- Simulated hardware manifest and example configurations
- Isolated LinuxCNC candidate generation
- QtVCP panel integration
- VMC850-style 12-pocket carousel Vismach model
- Simulation monitor, simulated tool-change sequence and M19 orientation demonstration
- Automated tests and GitHub Actions test workflow

## Important limitations

**This is a software demonstration, not a production ATC controller.**

- The included hardware manifest is simulated only. It does not describe a physical Mesa board or verified wiring.
- ATC Enable remains disabled and Live Apply is not implemented.
- Candidate generation copies a LinuxCNC simulation configuration and writes metadata. The generated HAL is intentionally inert except for loading the optional Vismach simulation display.
- The simulated tool-change and spindle-orientation sequences do not execute real LinuxCNC M6/M19 machine commands.
- The VMC850 model is schematic, not a dimensionally verified machine model.
- No safety interlock, collision avoidance, machine certification, or real hardware operation is provided.
- Do not connect this demo to servo drives, VFDs, pneumatic valves, tool changers, or other physical actuators.

Read [VMC850 Simulation](docs/VMC850-SIMULATION.md) and [Interlock / Recovery Notes](safety/01-INTERLOCK-RECOVERY.md) before experimenting.

## Requirements

For the GUI and Vismach demonstration:

- Linux with a working desktop session (X11/Qt display)
- LinuxCNC 2.9 simulation installation
- Python 3.9 or newer
- PyQt5, LinuxCNC Python/HAL modules, Vismach and PyOpenGL
- `jsonschema` and `pytest` for configuration validation and tests

The exact system packages vary by LinuxCNC distribution. On Debian/Ubuntu-based LinuxCNC systems, install the matching system packages for PyQt5, Python JSON Schema, PyOpenGL and pytest. Keep the system Python environment visible to the virtual environment.

## Quick start

Clone this repository:

```bash
git clone https://github.com/TC227/linuxcnc-universal-atc-demo.git
cd linuxcnc-universal-atc-demo
```

Create an environment that can see LinuxCNC's system Python modules and install the project:

```bash
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
```

If PyQt5 is not already available from the system Python, install the GUI extra as well:

```bash
python -m pip install -e ".[test,gui]"
```

Build an isolated VMC850 QtDragon simulation candidate:

```bash
python scripts/build_vmc850_sim.py
```

The script prints the generated configuration directory. Launch the reported `axis.ini` with LinuxCNC, for example:

```bash
linuxcnc ~/linuxcnc/configs/universal-atc-generated/vmc850-12-tool-sim-r001/axis.ini
```

If the installed QtDragon metric sample is in a different location, pass `--sample-dir`. To use an existing isolated simulation folder, pass `--base-config-dir` (it must contain `axis.ini`).

## Run tests

```bash
python -m pip install -e ".[test,gui]"
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

Or use the helper script:

```bash
bash scripts/test_ubuntu_local.sh
```

The automated GUI test uses Qt's offscreen platform; it does not launch LinuxCNC or access physical hardware.

## Validate an example configuration

```bash
atc-config validate \
  --config examples/configurations/vmc-12-rotary-dc-sim.json \
  --manifest examples/hardware-manifests/simulator-24di-16do.json
```

The example starts with an empty I/O mapping, so validation will report unmapped required signals until the wizard's Auto-map operation is used or a mapping is supplied.

## Repository layout

| Path | Purpose |
|---|---|
| `src/atc_configurator/` | Wizard, validator, I/O mapper, candidate generator and simulation runtime |
| `qtvcp/` | QtVCP panel integration |
| `scripts/` | VMC850 simulation builder and LinuxCNC test helpers |
| `examples/` | Example ATC configurations and simulated I/O resources |
| `profiles/` | Generic ATC profile catalogue |
| `schemas/` | JSON configuration, manifest and validation schemas |
| `docs/` | System, mechanism, configuration and simulation documentation |
| `software/` | Software architecture and GUI design notes |
| `tests/` | Automated unit and GUI smoke tests |

## Scope and licensing

This is a curated public source snapshot. See [Public Demo Scope](docs/PUBLIC-DEMO-SCOPE.md) for the publication boundary.

**No open-source license is included at this time.** Public visibility on GitHub does not by itself grant permission to copy, modify, redistribute, or use the code. A license can be added when the repository owner chooses one.
