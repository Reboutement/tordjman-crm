# Modèle de données reconstitué

Reconstitué le 2026-11-01 à partir de : `docs/crm-reference-for-tajfine.md` (champs, tags, routage), `Frenchbodyreset/docs/crm-structure.md` (pipelines), les étapes réelles de GHL lues le même jour, et le code de Frappe CRM 1.89.2. Le code d'origine de `tordjman_crm` 0.1.0 n'a pas été retrouvé : cette version 0.2.0 le **remplace**, elle ne le copie pas.

## Pipelines (étapes = « CRM Deal Status » nommés « Pipeline – Étape »)

Quatre pipelines, voulus par le propriétaire le 2026-11-07 : **Prospection** (6 étapes, celles de GHL), **Séances** (5), **Formation** (5), **B2B** (5). Les étapes des trois derniers sont une proposition simple à valider ; le détail et la correspondance avec GHL sont dans `docs/crm-cible-simplifiee.md` du dépôt `vitrine-seances-app`.

Les anciens pipelines (Transmission, Interv. pro, Webinaire, BDR, chatbot IA, LEARNING, suivi des élèves, « En ligne ») ne sont pas recréés : leurs opportunités s'importent avec un tag d'origine (étape 3 du plan). Le suivi des élèves après l'inscription se fait dans `formation-app`.

## Hypothèses à valider
1. **Types d'étapes** (Won / Lost / On Hold) : « Séance réalisée », « Inscrit (paiement reçu) » et « Intervention validée » = Won ; « Perdu / sans suite » = Lost ; le reste est Open ou Ongoing.
2. **Routage de l'intention** : documenté pour Private Session, Training et Partnership. **Hypothèses** : Workshop → Formation, Hospitality Partner → B2B, Other → Prospection.
3. **Types des champs** : la référence décrit les rôles, pas les types. Choix faits : texte court ou long, liste pour l'intention et la langue, case à cocher pour le consentement.
4. **Form Language** : `fr`, `es`, `en`, aligné sur les tags `lang_*`.
5. **Conflit d'intentions** : un contact portant plusieurs tags d'intention va en Prospection pour revue humaine, jamais dans deux pipelines.

## Champs
**Noyau validé le 2026-11-07 : 14 champs** sur **CRM Lead** et **CRM Deal**, préfixés `tj_`, dans une section repliable « Informations Tordjman », tous visibles dans le panneau latéral. Commun (11) : Intention, Main Objective, Timing / Urgency, Current Location, Chosen Format, Session Location Preference, Pre-Session Notes, Form Language, Marketing Consent, Known Contraindication, Prior Experience. B2B (3) : Company / Establishment, Establishment Type, Role / Function. Deux champs techniques : `tj_ghl_opportunity_id`, `tj_source_brute_ghl`. Sur les deals : `tj_pipeline`, calculé depuis l'étape.
Les autres champs de la référence ne sont pas créés (voir `docs/crm-cible-simplifiee.md`).
Champs de conservation GHL sur **Contact** (créés le 28/10 sur l'instance v16) : recréés seulement s'ils manquent.
**Donnée sensible** : « Known Contraindication » porte un avertissement ; elle ne doit jamais partir vers une plateforme publicitaire.

## Tags
23 tags canoniques créés. Un hook refuse les tags interdits (`intent-training`, `intent training`, `segment-hotel`, `intent_mini_stage`) et toute variante à tiret ou à espace d'un tag canonique. Les autres tags (131 en juillet) restent acceptés tels quels.

## API
`tordjman_crm.api.create_lead` : double écriture depuis `/api/lead`, **désactivée par défaut** (`tordjman_dual_write_enabled` dans `site_config.json`). Rôle requis : « Tordjman API ». Idempotente (identifiant GHL, puis e-mail ; un conflit n'écrit rien). `dry_run` ne modifie rien. Elle ne touche ni à GHL ni au booking.

## Non couvert
Import de l'existant (étape 3), automatisations (étape 4), canaux (étape 5), booking (étape 6) ; synchronisation Chatwoot ; règle anti-doublon d'opportunité par contact (GHL en a une, pas Frappe).
