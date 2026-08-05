#!/usr/bin/env bash
# Construit et ouvre le tableau de bord du projet.
#
#   ./run_dashboard.sh              construit puis ouvre outputs/dashboard/index.html
#   ./run_dashboard.sh --no-open    construit seulement (utile en CI ou sur un serveur)
#   ./run_dashboard.sh --serve      sert le dossier sur http://localhost:8000 au lieu
#                                   d'ouvrir un file:// (utile si le navigateur bloque
#                                   les iframes locales)
#
# Le script ne réentraîne rien et ne relance pas YOLO : il lit les sorties déjà
# produites par la chaîne evaluate_models.py -> export_gama_zones.py -> build_report.py.
# S'il manque une entrée, build_dashboard.py dit laquelle et quelle commande la produit.

set -euo pipefail
cd "$(dirname "$0")"

OPEN=1
SERVE=0
for a in "$@"; do
  case "$a" in
    --no-open) OPEN=0 ;;
    --serve)   SERVE=1 ;;
    -h|--help) sed -n '2,14p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "option inconnue : $a (voir --help)" >&2; exit 2 ;;
  esac
done

# --- environnement virtuel ---------------------------------------------------------
if [ ! -d .venv ]; then
  echo "==> .venv absent, création"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# --- dépendances -------------------------------------------------------------------
# On teste l'IMPORT plutôt que la présence dans pip list : c'est ce dont le script a
# réellement besoin, et cela évite un appel réseau quand tout est déjà en place.
MISSING=""
for mod in pandas numpy folium; do
  python -c "import $mod" 2>/dev/null || MISSING="$MISSING $mod"
done
if [ -n "$MISSING" ]; then
  echo "==> installation des dépendances manquantes :$MISSING"
  pip install --quiet $MISSING
fi

# --- construction ------------------------------------------------------------------
echo "==> construction du tableau de bord"
python scripts/build_dashboard.py

PAGE="outputs/dashboard/index.html"
[ -f "$PAGE" ] || { echo "échec : $PAGE non généré" >&2; exit 1; }

# --- ouverture ---------------------------------------------------------------------
if [ "$SERVE" -eq 1 ]; then
  echo "==> http://localhost:8000/index.html   (Ctrl+C pour arrêter)"
  [ "$OPEN" -eq 1 ] && { (sleep 1 && xdg-open "http://localhost:8000/index.html" >/dev/null 2>&1 || true) & }
  exec python -m http.server 8000 --directory outputs/dashboard
fi

if [ "$OPEN" -eq 1 ]; then
  URL="file://$(pwd)/$PAGE"
  echo "==> ouverture de $URL"
  # xdg-open sous Linux, open sous macOS ; si aucun des deux, on affiche le chemin.
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 &
  elif command -v open   >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 &
  else echo "    (aucun ouvreur détecté — ouvrir manuellement : $PAGE)"; fi
else
  echo "==> construit : $PAGE"
fi
