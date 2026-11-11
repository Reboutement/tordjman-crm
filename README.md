# tordjman-crm — app Frappe `tordjman_crm` et reconstruction de l'image

Ce dépôt contient (1) l'app Frappe `tordjman_crm` reconstituée (pipelines, champs, tags, API de double écriture), à la racine, et (2) dans `image/`, comment reconstruire l'image Docker `tordjman-crm` qui fait tourner les préproductions Frappe CRM (Coolify, VPS 62.72.18.234), et comment retrouver ce qui manque pour qu'elle soit entièrement reproductible. **Statut : préparé le 2026-11-01, jamais exécuté** (aucun Docker dans la session qui l'a écrit).

Il ne contient aucun secret, aucune donnée de client et ne touche à aucune instance existante : le tag par défaut est nouveau (`preprod-v16-rebuild`).

## Ce qu'on sait

| Élément | Valeur |
|---|---|
| Framework | `frappe/frappe`, branche `version-16`, en service : 16.54.0 |
| Application | `frappe/crm`, étiquette `v1.89.2` |
| Construction | `frappe/frappe_docker`, `images/layered/Containerfile` |
| Images observées | `tordjman-crm:preprod` (Frappe 15.124.0, CRM 1.86.0), `:preprod-v16`, `:preprod-v16-tags-fix` (Frappe 16.54.0, CRM 1.89.2, app `tordjman_crm` 0.1.0) |

Versions figées dans `versions.lock` (commits résolus le 2026-11-01).

## Ce qui n'est pas reproductible, et pourquoi

1. **Le correctif `tags-fix` est inconnu.** La commande d'origine ne construit que `preprod-v16`. Le correctif, l'app `tordjman_crm` et les personnalisations stockées en base (champs, pipelines, statuts) doivent être retrouvés : voir `docs/tags-fix.md`.
2. **Frappe suit une branche.** L'image de base `frappe/build:<étiquette>` n'existe pas pour `v16.54.0`, donc la construction utilise `version-16` : une reconstruction future peut embarquer une version plus récente. `build.sh` le détecte après coup (`STRICT=1` pour échouer).
3. **Les commits utilisés le 27/10 n'ont pas été conservés.** Les SHA de `versions.lock` sont ceux d'aujourd'hui pour la version en service, pas une preuve de ceux d'origine.

## L'app `tordjman_crm` 0.2.0

Reconstituée, pas copiée : le code d'origine n'a pas été retrouvé. Détail, hypothèses et limites : `docs/modele-donnees.md`. Branches : `docs/branches.md`.

```bash
cd tordjman_crm && python3 -m unittest discover -s tests -t ..   # logique pure, sans Frappe : 17 tests
```

Le code qui dépend de Frappe (`install.py`, `events.py`, `api.py`) est vérifié par compilation et par lecture des sources de Frappe 16.54.0 et de CRM 1.89.2, **jamais exécuté sur un bench**. À tester sur une instance isolée (restaurée depuis une sauvegarde) avant la préproduction.

## Utilisation de l'image

```bash
VERIFY_ONLY=1 image/build.sh          # contrôle seulement que les versions amont correspondent, ne construit rien
TAG=preprod-v16-rebuild image/build.sh # construit une NOUVELLE image, sans écraser les existantes
image/scripts/verify-image.sh tordjman-crm:preprod-v16-rebuild
```

Pour inclure l'app dans l'image, une fois le dépôt `Reboutement/tordjman-crm` créé et l'étiquette `v0.2.0` posée : copier `image/apps.with-tordjman.json` sur `image/apps.json` (dépôt privé : jeton de lecture en secret BuildKit, jamais dans le fichier).

Récupérer l'existant (VPS, lecture seule, ne démarre aucun conteneur) :

```bash
image/scripts/extract-from-images.sh   # écrit dans ./recovered/ (ignoré par Git, à relire avant partage)
```

## Règles

- Ne jamais supprimer ni écraser les images `tordjman-crm:*` existantes avant d'avoir extrait leur contenu : elles sont, pour l'instant, la seule copie du correctif.
- Aucun secret dans ce dossier : les mots de passe restent dans les variables d'environnement Coolify.
- Les bases de données (champs personnalisés, pipelines, statuts) se sauvegardent séparément : voir `docs/crm-backup-procedure.md` du dépôt `vitrine-seances-app`.
