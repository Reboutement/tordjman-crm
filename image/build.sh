#!/usr/bin/env bash
# Construit l'image tordjman-crm à partir de versions FIGÉES (versions.lock).
# À lancer sur une machine avec Docker + BuildKit. N'écrase aucune image existante : le tag par défaut est nouveau.
# Non exécuté depuis la session qui l'a écrit : vérifier d'abord avec VERIFY_ONLY=1.
# Limite connue : l'image de base Docker `frappe/build:<branche>` n'existe pas pour l'étiquette v16.54.0
# (vérifié le 2026-11-01), donc Frappe suit la branche `version-16` au moment de la construction. Seuls
# frappe_docker et crm sont figés. Le contrôle final compare la version obtenue à FRAPPE_SHA ; avec STRICT=1,
# un écart (la branche a avancé) fait échouer la construction.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck disable=SC1091
. ./versions.lock

TAG="${TAG:-preprod-v16-rebuild}"
IMAGE="${IMAGE:-tordjman-crm}"
BUILD_DIR="${BUILD_DIR:-build/frappe_docker}"

if [ "${VERIFY_ONLY:-0}" = "1" ]; then
  echo "Image cible : $IMAGE:$TAG"
  echo "frappe_docker $FRAPPE_DOCKER_SHA ; frappe branche $FRAPPE_BRANCH, attendu $FRAPPE_TAG ($FRAPPE_SHA) ; crm $CRM_TAG ($CRM_SHA)"
  git ls-remote "$FRAPPE_REPO" "refs/tags/$FRAPPE_TAG" | grep -q "$FRAPPE_SHA" && echo "OK frappe" || { echo "ECART frappe"; exit 1; }
  git ls-remote "$CRM_REPO" "refs/tags/$CRM_TAG" | grep -q "$CRM_SHA" && echo "OK crm" || { echo "ECART crm"; exit 1; }
  exit 0
fi

rm -rf "$BUILD_DIR" && mkdir -p "$BUILD_DIR"
git -C "$BUILD_DIR" init -q
git -C "$BUILD_DIR" remote add origin "$FRAPPE_DOCKER_REPO"
git -C "$BUILD_DIR" fetch -q --depth 1 origin "$FRAPPE_DOCKER_SHA"
git -C "$BUILD_DIR" checkout -q FETCH_HEAD

DOCKER_BUILDKIT=1 docker build \
  --build-arg "FRAPPE_PATH=$FRAPPE_REPO" \
  --build-arg "FRAPPE_BRANCH=$FRAPPE_BRANCH" \
  --secret id=apps_json,src="$PWD/apps.json" \
  --tag "$IMAGE:$TAG" \
  --file "$BUILD_DIR/images/layered/Containerfile" \
  "$BUILD_DIR"

got=$(docker run --rm --entrypoint bash "$IMAGE:$TAG" -c 'git -C /home/frappe/frappe-bench/apps/frappe rev-parse HEAD 2>/dev/null' || true)
if [ "$got" = "$FRAPPE_SHA" ]; then
  echo "Frappe identique à la version figée ($FRAPPE_TAG)."
else
  echo "ATTENTION : Frappe = ${got:-inconnu}, attendu $FRAPPE_SHA ($FRAPPE_TAG). La branche $FRAPPE_BRANCH a avancé ou l'image n'a pas de dépôt git."
  [ "${STRICT:-0}" = "1" ] && exit 1
fi
echo "Image construite : $IMAGE:$TAG"
echo "Contrôler ensuite avec : ./scripts/verify-image.sh $IMAGE:$TAG"
