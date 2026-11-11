# Branches

| Branche | Rôle | Qui y écrit |
|---|---|---|
| `main` | Version stable, étiquetée (`v0.2.0`…). C'est elle que l'image de production construit. | Fusion uniquement, après tests |
| `preprod` | Ce que la préproduction Coolify construit et déploie | Fusion depuis `main` ou depuis une branche de test |
| `feat/<sujet>`, `fix/<sujet>` | Travail en cours, une idée par branche | Claude Code, Grégory |

Règles : tests verts avant toute fusion dans `main` ; jamais de secret ; `apps.json` de production pointe une étiquette ou un commit, jamais une branche ; l'image ne se reconstruit pas sans tag nouveau. Ces règles sont des propositions à valider.
