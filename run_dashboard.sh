#!/usr/bin/env bash
# Build and open the project dashboard.
#
#   ./run_dashboard.sh              build, then open results/report/dashboard/index.html
#   ./run_dashboard.sh --no-open    build only (useful in CI or on a server)
#   ./run_dashboard.sh --serve      serve the folder on http://localhost:8000 instead
#                                   of opening a file:// URL (useful if the browser blocks
#                                   local iframes)
#
# The script retrains nothing and does not rerun YOLO: it reads the outputs already
# produced by the chain 04_evaluate_models.py -> 07_export_gama_inputs.py -> 10_build_report.py.
# If an input is missing, 11_build_dashboard.py says which one and what produces it.

set -euo pipefail
cd "$(dirname "$0")"

OPEN=1
SERVE=0
for a in "$@"; do
  case "$a" in
    --no-open) OPEN=0 ;;
    --serve)   SERVE=1 ;;
    -h|--help) sed -n '2,14p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "unknown option: $a (see --help)" >&2; exit 2 ;;
  esac
done

# --- virtual environment -----------------------------------------------------------
if [ ! -d .venv ]; then
  echo "==> .venv missing, creating it"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# --- dependencies ------------------------------------------------------------------
# We test the IMPORT rather than presence in pip list: that is what the script actually
# needs, and it avoids a network call when everything is already in place.
MISSING=""
for mod in pandas numpy folium; do
  python -c "import $mod" 2>/dev/null || MISSING="$MISSING $mod"
done
if [ -n "$MISSING" ]; then
  echo "==> installing missing dependencies:$MISSING"
  pip install --quiet $MISSING
fi

# --- build ---------------------------------------------------------------------------
echo "==> building the dashboard"
python scripts/11_build_dashboard.py

PAGE="results/report/dashboard/index.html"
[ -f "$PAGE" ] || { echo "failed: $PAGE was not generated" >&2; exit 1; }

# --- open ----------------------------------------------------------------------------
if [ "$SERVE" -eq 1 ]; then
  echo "==> http://localhost:8000/index.html   (Ctrl+C to stop)"
  [ "$OPEN" -eq 1 ] && { (sleep 1 && xdg-open "http://localhost:8000/index.html" >/dev/null 2>&1 || true) & }
  exec python -m http.server 8000 --directory results/report/dashboard
fi

if [ "$OPEN" -eq 1 ]; then
  URL="file://$(pwd)/$PAGE"
  echo "==> opening $URL"
  # xdg-open on Linux, open on macOS; if neither exists, print the path.
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 &
  elif command -v open   >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 &
  else echo "    (no opener detected - open manually: $PAGE)"; fi
else
  echo "==> built: $PAGE"
fi
