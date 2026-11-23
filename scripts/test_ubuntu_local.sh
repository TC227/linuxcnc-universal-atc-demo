#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${ATC_TEST_VENV:-$ROOT/.venv-test}"
cd "$ROOT"

echo "== Universal ATC: Ubuntu local test =="
echo "Repository: $ROOT"
echo "Python: $(python3 --version)"

python3 -m venv --system-site-packages "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

python -m pip install --upgrade pip
if python -c "import PyQt5" 2>/dev/null; then
    python -m pip install -e ".[test]"
else
    python -m pip install -e ".[test,gui]"
fi

echo
echo "== Compile Python and QtVCP files =="
python -m compileall -q src qtvcp scripts

echo
echo "== Check Pi 4 installer shell syntax =="
bash -n scripts/install_pi4_axis_test.sh

echo
echo "== Run headless tests =="
QT_QPA_PLATFORM=offscreen python -m pytest -q

echo
echo "== Test summary =="
echo "Python package, PyQt5 offscreen GUI tests, generator tests and shell syntax passed."
echo
echo "To open the standalone wizard against the installed LinuxCNC AXIS simulation:"
echo "  source \"$VENV/bin/activate\""
echo "  python -m atc_configurator.gui --data-dir \"$ROOT\" \\"
echo "    --base-config-dir /usr/share/linuxcnc/configs/sim/axis \\"
echo "    --output-root \"$HOME/linuxcnc/configs/universal-atc-generated\""
echo
echo "If your AXIS simulation directory is elsewhere, replace --base-config-dir."
echo "This GUI test does not start LinuxCNC or connect to physical hardware."
