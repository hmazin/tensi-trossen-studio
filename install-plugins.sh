#!/usr/bin/env bash
# Install TENSI plugins into the lerobot_trossen environment.
# Run this once after cloning, or after updating plugin code.
#
# Usage:
#   ./install-plugins.sh
#   LEROBOT_TROSSEN_PATH=/custom/path ./install-plugins.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEROBOT_DIR="${LEROBOT_TROSSEN_PATH:-$HOME/lerobot_trossen}"

echo "=== Installing TENSI plugins ==="
echo "  Plugin source: $SCRIPT_DIR/lerobot_plugins/"
echo "  LeRobot env:   $LEROBOT_DIR"
echo ""

if [ ! -d "$LEROBOT_DIR" ]; then
    echo "[ERROR] lerobot_trossen not found at $LEROBOT_DIR"
    echo "  Set LEROBOT_TROSSEN_PATH to the correct location."
    exit 1
fi

cd "$LEROBOT_DIR"

echo "[1/2] Installing remote leader teleoperator plugin..."
uv pip install -e "$SCRIPT_DIR/lerobot_plugins/lerobot_teleoperator_remote/"
echo ""

echo "[2/2] Verifying installation..."
uv run python -c "
from lerobot_teleoperator_remote import RemoteLeaderTeleop, RemoteLeaderTeleopConfig
print('  RemoteLeaderTeleop:', RemoteLeaderTeleop.name)
print('  Plugin registered successfully!')
"
echo ""
echo "=== Done ==="
