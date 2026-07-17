#!/usr/bin/env bash
# Export de la présentation Marp vers PowerPoint (.pptx) et PDF.
#
# Prérequis : Marp CLI
#   npm install -g @marp-team/marp-cli
#   (ou sans installation globale : npx @marp-team/marp-cli ...)
#
# Usage :
#   bash export.sh            # génère presentation.pptx + presentation.pdf
#   bash export.sh pptx       # uniquement le PowerPoint
#   bash export.sh pdf        # uniquement le PDF
#
# Les fichiers exportés (.pptx / .pdf) sont gitignored : seul slides.md est versionné.

set -euo pipefail

cd "$(dirname "$0")"

SRC="slides.md"
TARGET="${1:-all}"

# Résout la commande marp : binaire global si présent, sinon npx.
if command -v marp >/dev/null 2>&1; then
  MARP="marp"
else
  echo "marp introuvable — utilisation de 'npx @marp-team/marp-cli'"
  MARP="npx --yes @marp-team/marp-cli"
fi

export_pptx() {
  echo "Export PowerPoint -> presentation.pptx"
  $MARP "$SRC" --pptx --allow-local-files -o presentation.pptx
}

export_pdf() {
  echo "Export PDF -> presentation.pdf"
  $MARP "$SRC" --pdf --allow-local-files -o presentation.pdf
}

case "$TARGET" in
  pptx) export_pptx ;;
  pdf)  export_pdf ;;
  all)  export_pptx; export_pdf ;;
  *)    echo "Cible inconnue: $TARGET (attendu: pptx | pdf | all)"; exit 1 ;;
esac

echo "Terminé."
