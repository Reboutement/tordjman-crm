# Procédure de sauvegarde et de restauration — Frappe B (v16) et Chatwoot

> Statut : **préparée le 2026-10-29, NON EXÉCUTÉE.** Chaque étape qui écrit quelque chose demande l'accord de Grégory.
> Cible : `crm-preprod-v16-mariadb118` (service Coolify `ch8g7kdi5n0bhxeullv9o1xx`), puis Chatwoot (`xqphjgngoqpqcqbuvycfukqc`).
> Aucun secret dans ce document. Les identifiants S3 se saisissent dans l'interface, jamais dans une conversation ni un fichier.

## Pourquoi maintenant

B porte les seules données GHL migrées (11 contacts, dont 10 avec leur payload d'origine). Elle n'a aucune sauvegarde prouvée : la tâche planifiée Coolify « Sauvegarde quotidienne CRM préproduction » (tous les jours à 01:30, conteneur `backend`) a réussi deux fois le 28/10 mais n'a pas tourné le 29/10, et sa commande n'est pas lisible par l'API. Chatwoot n'a aucune sauvegarde non plus.

## Ce qu'il faut sauvegarder

| Élément | Où | Contenu |
|---|---|---|
| Base MariaDB de B | volume `…_crm-v16-118-db` (conteneur `db`) | contacts, deals, champs `custom_ghl_*`, statuts, tags |
| Fichiers du site B | volume `…_crm-v16-118-sites` (conteneur `backend`) | `site_config.json`, fichiers privés et publics |
| Base PostgreSQL de Chatwoot | conteneur `postgres` de `crm-communications-preprod` | conversations, contacts, boîtes, attributs |
| Stockage de fichiers de Chatwoot | volume de l'application | pièces jointes |

Les sauvegardes planifiées natives de Coolify **ne couvrent pas** les bases embarquées dans un service : il faut donc passer par des commandes.

## Niveau 1 — copie immédiate sur le serveur (réversible, sans risque)

Objectif : avoir au moins un fichier de sauvegarde lisible dans les 15 minutes. **Protège contre une erreur humaine ou un échec d'import ; ne protège pas contre la perte du serveur.**

À faire dans Coolify > service `crm-preprod-v16-mariadb118` > Terminal, conteneur `backend` :

1. Trouver le nom du site (lecture) :
   `ls sites/`
   Retenir le dossier qui n'est ni `assets` ni un fichier. Il est probablement `crm-v16.62.72.18.234.sslip.io` (à confirmer).
2. Lire ce que la tâche planifiée actuelle produit (lecture) :
   `ls -la sites/<SITE>/private/backups/ 2>/dev/null | tail -20`
3. Sauvegarde complète (base + fichiers) :
   `bench --site <SITE> backup --with-files`
   Puis relire : `ls -la sites/<SITE>/private/backups/`
   Attendu : trois fichiers récents `…-database.sql.gz`, `…-files.tar`, `…-private-files.tar`, et `…-site_config_backup.json`.
4. Vérifier que la base est lisible :
   `gzip -t sites/<SITE>/private/backups/<fichier>-database.sql.gz && echo OK`

Critère de réussite : fichier de base non vide (taille > 0), `gzip -t` répond OK, date du jour.

### Chatwoot (niveau 1)

Dans le conteneur `postgres` du service `crm-communications-preprod` :
`pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > /tmp/chatwoot-$(date +%F).dump && ls -la /tmp/chatwoot-*.dump`
Si `$POSTGRES_USER` ou `$POSTGRES_DB` ne sont pas définies dans le conteneur, lire leurs **noms** (pas les valeurs) dans l'onglet Environment Variables du service, puis les substituer.

## Niveau 2 — copie hors du serveur (indispensable avant la production)

Objectif : survivre à la perte du VPS. Deux stockages S3 existent déjà dans Coolify : `FBR Backups Production` (bucket `fbr-backups-prod`) et `fbr-sauvegardes` (bucket `fbr-sauvegardes-tordjman`), tous deux utilisables. **Recommandation : `fbr-sauvegardes`, préfixe `crm-preprod/`**, pour ne pas mélanger la production et le test.

Deux voies, de la plus simple à la plus lourde :

| Voie | Principe | Limite |
|---|---|---|
| A — Intégration S3 de Frappe | « S3 Backup Settings » dans Frappe, planifiée quotidiennement ; les identifiants S3 sont saisis par Grégory dans le formulaire | Le bureau `/app` est inutilisable tant que l'assistant de configuration n'est pas terminé. Cette intégration est absente de B d'après l'audit (présente mais désactivée sur A) : à confirmer en v16 |
| B — Base autonome Coolify | Remplacer la MariaDB embarquée par une base MariaDB autonome de Coolify, dont les sauvegardes S3 planifiées sont natives et déjà éprouvées (voir `seances-db`, 66 exécutions) | Changement d'architecture : à planifier, pas en urgence |

Par défaut, faire **la voie A** après avoir terminé l'assistant de configuration, puis étudier la voie B.

## Restauration — test obligatoire

Une sauvegarde non restaurée n'est pas une sauvegarde. Test **isolé**, sans canaux sortants :

1. Utiliser le service arrêté `crm-preprod-v16-isole` (3 volumes propres) comme bac à sable, **sans le démarrer tant que l'e-mail sortant n'est pas coupé**. Il n'a pas de domaine public.
2. Copier le fichier de sauvegarde vers le conteneur du bac à sable (par le S3 du niveau 2, ou en téléchargement depuis Frappe une fois le bureau accessible).
3. Dans son conteneur `backend` : `bench --site <SITE_TEST> --force restore <fichier>-database.sql.gz --with-private-files … --with-public-files …`
4. Vérifier : le nombre de contacts (11) et la présence des 8 champs `custom_ghl_*`.
5. Consigner le résultat dans `crm-frappe-migration-plan.md` (date, fichier, résultat, durée).

## Planification

- Frappe B : sauvegarde quotidienne, rétention 7 jours en local et 30 jours sur S3.
- Chatwoot : quotidienne, même rétention.
- **Réparer ou remplacer** la tâche Coolify existante : relire son historique, comprendre pourquoi elle n'a pas tourné le 29/10 à 01:30, ou la recréer avec une commande explicite visible.

## Garde-fous

- Ne rien supprimer, ne rien redémarrer, ne pas cliquer sur Save / Reset des pages Coolify qui affichent « changements non enregistrés ».
- Ne pas lancer « Update All Packages » (redémarre tous les conteneurs, production comprise).
- Avant d'activer le scheduler de B, couper l'e-mail sortant (un compte actif existe par défaut).
- Ne pas commiter de fichier de sauvegarde (données personnelles).

## Ordre d'exécution proposé

1. Niveau 1 pour B (5 minutes).
2. Niveau 1 pour Chatwoot.
3. Terminer l'assistant de configuration de B (décision du propriétaire).
4. Niveau 2, voie A.
5. Test de restauration dans le bac à sable.
6. Seulement ensuite : retrait réversible de la préprod A et du service `v16-isole` si inutile.
