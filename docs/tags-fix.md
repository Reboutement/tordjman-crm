# Retrouver le correctif `tags-fix`

## Ce qu'on sait
- L'image `tordjman-crm:preprod-v16-tags-fix` existe sur le VPS et sert `crm-preprod-v16-mariadb118`.
- La commande retrouvée construit `tordjman-crm:preprod-v16`, pas cette variante.
- L'étiquette suggère un correctif sur la gestion des tags, qui sont au cœur du routage (`intent_training`, `intent_private_session`…). La nature exacte du correctif est **inconnue**.
- L'app `tordjman_crm` 0.1.0 est installée sur cette instance. Son code source n'a été trouvé dans aucun dépôt.

## Pistes, par ordre
1. **Extraire la différence entre les deux images** : `./scripts/extract-from-images.sh` sur le VPS (lecture seule). Lire `recovered/tags-fix-crm.diff`, `tags-fix-frappe.diff` et les `*.history.txt` (couches et commandes de construction).
2. **Le dossier de construction** cité par le journal du 27/10 : `/tmp/crm-v16-build-c7xWHQ` (peut avoir disparu).
3. **Les conteneurs en marche** : `/home/frappe/frappe-bench/apps/` ; comparer les fichiers à leurs sources amont.
4. **Ce qui vit en base** et non dans le code : champs personnalisés, scripts serveur et client, statuts, vues. À exporter depuis l'instance (Customize Form, fixtures) et à versionner.
5. **Historique des commandes et des sessions** du poste qui a construit l'image.

## Quand on l'a retrouvé
- Le mettre dans une **app Frappe versionnée** (`tordjman_crm`) installée via `apps.json`, plutôt que dans un correctif sur l'image.
- Ajouter l'app à `apps.json` avec un commit précis, reconstruire sous un nouveau tag, tester sur une instance isolée, puis seulement basculer.
