# Public Demo Scope

## Purpose

This repository is a clean, public demonstration snapshot of the LinuxCNC Universal ATC configurator and its VMC850 simulation. It is intended for review, education, GUI experimentation and software testing.

## Source snapshot

- Development source: `linuxcnc-universal-atc`
- Source branch: `feature/vmc850-atc-simulation`
- Source commit: `13ea6540dc76942694cbad45f58e74392a62954e`
- Export date: 2026-11-23

Only selected text/source assets were copied. The new repository has its own independent Git history.

## Included

- Python configurator, validation engine, simulation runtime and tests
- QtVCP panel integration
- Generic ATC profiles and JSON schemas
- Simulation-only hardware manifest and sample configurations
- VMC850 schematic Vismach model and setup instructions
- General ATC mechanism and software design documentation

## Deliberately excluded

- Git commit history, development branches, pull requests and internal issue discussions
- PCB schematics, board layouts, component lists, pin maps and hardware resource-budget documents
- The unverified 7i92/7i76 clone hardware manifest
- Private machine-specific configuration, network addresses, credentials and personal paths
- Internal roadmap and unrelated project notes

## Safety boundary

The simulator manifest is explicitly marked `simulated`. It must not be interpreted as a verified hardware definition. ATC Enable and Live Apply remain disabled. Candidate generation is intended for isolated LinuxCNC simulation configurations only.

This demo is not suitable for direct machine operation or safety-critical use.

## Licensing

No license has been selected or added. Until the repository owner adds a license, do not assume that public access grants reuse rights.
