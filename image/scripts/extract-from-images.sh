#!/usr/bin/env bash
# LECTURE SEULE. À lancer sur le VPS pour retrouver ce que contiennent les images existantes
# et isoler le correctif "tags-fix". Ne démarre aucun conteneur (docker create + docker cp), ne touche à aucun volume.
# Les résultats vont dans ./recovered/ (ignoré par Git : à relire avant tout partage).
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=recovered; mkdir -p "$OUT"
IMAGES="tordjman-crm:preprod tordjman-crm:preprod-v16 tordjman-crm:preprod-v16-tags-fix"

for img in $IMAGES; do
  safe="${img//[:\/]/_}"
  docker image inspect "$img" >"$OUT/$safe.inspect.json" 2>/dev/null || { echo "absente : $img"; continue; }
  docker history --no-trunc "$img" >"$OUT/$safe.history.txt"
  cid=$(docker create "$img")
  rm -rf "$OUT/$safe" && mkdir -p "$OUT/$safe"
  for app in frappe crm; do
    docker cp "$cid:/home/frappe/frappe-bench/apps/$app" "$OUT/$safe/$app" 2>/dev/null || echo "pas d'application $app dans $img"
  done
  docker rm "$cid" >/dev/null
  echo "extrait : $img"
done

# Différence entre la variante corrigée et sa base (sans l'historique git ni les dépendances installées)
if [ -d "$OUT/tordjman-crm_preprod-v16" ] && [ -d "$OUT/tordjman-crm_preprod-v16-tags-fix" ]; then
  for app in frappe crm; do
    diff -ruN --exclude=.git --exclude=node_modules --exclude=__pycache__ --exclude='*.pyc' \
      "$OUT/tordjman-crm_preprod-v16/$app" "$OUT/tordjman-crm_preprod-v16-tags-fix/$app" \
      >"$OUT/tags-fix-$app.diff" || true
    echo "diff $app : $(wc -l <"$OUT/tags-fix-$app.diff") lignes (voir $OUT/tags-fix-$app.diff)"
  done
fi
