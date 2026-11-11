#!/usr/bin/env bash
# Affiche les versions et commits réellement présents dans une image (lecture seule, conteneur jetable sans volume).
set -euo pipefail
IMG="${1:?usage: verify-image.sh <image:tag>}"
docker run --rm --entrypoint bash "$IMG" -c '
cd /home/frappe/frappe-bench 2>/dev/null || exit 1
for a in frappe crm; do
  echo "== $a"
  cat apps/$a/$a/__init__.py 2>/dev/null | grep -i "__version__" || true
  git -C apps/$a rev-parse HEAD 2>/dev/null || echo "(pas de dépôt git dans cette image)"
  git -C apps/$a status --short 2>/dev/null | head -20 || true
done
ls apps
'
