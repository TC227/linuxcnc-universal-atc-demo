#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "Run this script as the LinuxCNC user (cnc), not as root."
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIM_SOURCE="${LINUXCNC_SIM_AXIS_DIR:-/usr/share/linuxcnc/configs/sim/axis}"
TARGET="${HOME}/linuxcnc/configs/universal-atc-axis-test"

for command_name in linuxcnc qtvcp halcmd; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name"
    echo "Check that LinuxCNC 2.9 and QtVCP are installed."
    exit 3
  fi
done

if ! python3 -c "import PyQt5, jsonschema" >/dev/null 2>&1; then
  echo "Python dependencies are missing."
  echo "Install with: sudo apt install python3-pyqt5 python3-jsonschema"
  exit 4
fi

if [ ! -f "$SIM_SOURCE/axis.ini" ]; then
  echo "Could not find the installed Axis simulation config:"
  echo "  $SIM_SOURCE/axis.ini"
  echo "Set LINUXCNC_SIM_AXIS_DIR to the directory containing the LinuxCNC sim/axis/axis.ini file."
  exit 5
fi

if [ -e "$TARGET" ]; then
  echo "Refusing to overwrite an existing test directory:"
  echo "  $TARGET"
  echo "Move it aside or choose a new TARGET in this script before retrying."
  exit 6
fi

mkdir -p "$(dirname "$TARGET")"
mkdir -p "$TARGET"
cp -a "$SIM_SOURCE/." "$TARGET/"

# Copy only the configurator runtime/data and its local QtVCP panel.
cp -a "$REPO_ROOT/src" "$TARGET/"
cp -a "$REPO_ROOT/schemas" "$TARGET/"
cp -a "$REPO_ROOT/profiles" "$TARGET/"
cp -a "$REPO_ROOT/examples" "$TARGET/"
mkdir -p "$TARGET/qtvcp/panels"
cp -a "$REPO_ROOT/qtvcp/panels/universal_atc" "$TARGET/qtvcp/panels/"

python3 - "$TARGET/axis.ini" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()

def set_key(section, key, value):
    section_re = re.compile(r"^\s*\[" + re.escape(section) + r"\]\s*$", re.I)
    start = next((i for i, line in enumerate(lines) if section_re.match(line)), None)
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([f"[{section}]", f"{key} = {value}"])
        return
    end = next(
        (i for i in range(start + 1, len(lines)) if re.match(r"^\s*\[.+\]\s*$", lines[i])),
        len(lines),
    )
    key_re = re.compile(r"^\s*" + re.escape(key) + r"\s*=", re.I)
    matches = [i for i in range(start + 1, end) if key_re.match(lines[i])]
    replacement = f"{key} = {value}"
    if matches:
        lines[matches[0]] = replacement
        for i in reversed(matches[1:]):
            del lines[i]
    else:
        lines.insert(start + 1, replacement)

set_key("EMC", "MACHINE", "Universal-ATC-Axis-Simulation")
set_key("DISPLAY", "EMBED_TAB_NAME", "Universal ATC")
set_key(
    "DISPLAY",
    "EMBED_TAB_COMMAND",
    "halcmd loadusr -Wn qtvcp_embed qtvcp -d -c qtvcp_embed -x {XID} universal_atc",
)
set_key("HAL", "POSTGUI_HALFILE", "atc_generated.hal")
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

cat > "$TARGET/atc_generated.hal" <<'HAL'
# Safe no-op HAL file for the Universal ATC Axis simulation test.
# The Apply button will generate a separate candidate folder and its own HAL file.
# No active HAL commands, physical I/O, motion or ATC runtime are loaded here.
HAL

cat > "$TARGET/README_ATC_TEST.md" <<'DOC'
# Universal ATC - AXIS Simulation Test

This is a separate copy of the stock LinuxCNC AXIS simulation configuration.
It is not an original machine configuration.

Launch from the Pi desktop terminal:

    linuxcnc axis.ini

The Universal ATC tab is embedded through QtVCP X11 embedding.
The wizard starts with the chain / 24-pocket example and the simulator manifest.

To test Apply:
1. Open page 7 and press Auto-map.
2. Open page 8 and press Validate Configuration.
3. If Configuration Valid is YES, press Apply -> Generate Test Config.
4. The wizard creates a separate folder under generated/.
5. The generated axis.ini can be opened separately with LinuxCNC.

This is simulation-only. ATC Enable and Live Apply remain disabled.
The generated HAL file is comment-only. No physical outputs or motion are commanded.
DOC

echo
echo "Universal ATC Axis test configuration installed:"
echo "  $TARGET/axis.ini"
echo
echo "Open it from the Pi desktop terminal with:"
echo "  linuxcnc \"$TARGET/axis.ini\""
echo
echo "Do not connect or enable servo drives, VFDs, 24V ATC outputs or actuators for this test."
