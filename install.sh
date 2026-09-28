#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

ROOT="/opt/imagerpi"
LAUNCHER="/usr/local/bin/imagerpi"

$SUDO apt update
$SUDO apt install -y python3 python3-pil

$SUDO rm -rf "$ROOT"
$SUDO mkdir -p "$ROOT"
$SUDO cp -r src "$ROOT/"
$SUDO chmod -R a+rX "$ROOT"

$SUDO tee "$LAUNCHER" >/dev/null <<EOF
#!/usr/bin/env bash
set -euo pipefail
ROOT="$ROOT"
export PYTHONPATH="$ROOT/src"
exec python3 -m imagerpi "$@"
EOF

$SUDO chmod +x "$LAUNCHER"

echo
echo "IMAGE.RPI installed system-wide. Try:"
echo "  imagerpi /path/to/image.jpg"
