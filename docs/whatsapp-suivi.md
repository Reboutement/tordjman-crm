# Suivi des conversations WhatsApp dans le CRM

Statut : code écrit et testé en logique pure (24 tests). **Non exécuté sur Frappe, non branché à WhatsApp.**

## Ce que ça fait
Une pub Meta « clic vers WhatsApp » ouvre WhatsApp. Le **premier message** de la conversation peut porter un bloc `referral`
(`source_id` = identifiant de la pub, `ctwa_clid` = identifiant du clic, `headline`, `source_url`). `api.whatsapp_lead` :
1. extrait ces champs (`whatsapp.py`) ;
2. retrouve le contact par téléphone, sinon le crée ;
3. crée une opportunité dans le pipeline Séances (étape « Nouveau lead »), avec `Canal d'entree` = WhatsApp, `Pub Meta ID`, `Clic pub ID`, `Titre de la pub`, `URL source` ;
4. est idempotent (même téléphone + même pub = pas de doublon) ; un message sans `referral` est gardé comme lead organique ;
5. n'écrit rien si `tordjman_dual_write_enabled` est absent de `site_config.json` ; `dry_run=true` ne fait que planifier.

Cinq champs techniques ajoutés (pas des champs métier GHL) : `tj_canal_d_entree`, `tj_pub_meta_id`, `tj_clic_pub_id`, `tj_titre_de_la_pub`, `tj_url_source`. Créés par `after_migrate`.

## Ce qui reste à brancher (décision et accès du propriétaire)
- **Source des messages.** Deux options, à trancher selon ce que Chatwoot conserve : (a) relais depuis le webhook WhatsApp Cloud API (la charge brute est acceptée telle quelle) ; (b) relais Chatwoot qui renvoie téléphone + referral. Chatwoot peut ne pas stocker `referral` : **à vérifier sur un vrai message avant de choisir.**
- **Numéro.** Le numéro doit être sur l'API WhatsApp Business (Cloud API), pas sur l'application WhatsApp Business seule, sinon Meta ne remonte rien.
- **Lecture côté Meta.** Une fois `Pub Meta ID` rempli, le coût par conversation et par séance se calcule pub par pub (v4 contre variantes).
- **Pas de promesse sur l'historique** : les conversations déjà dans GHL n'ont pas ce champ.

## Test sûr (données fictives, instance isolée)
`POST /api/method/tordjman_crm.api.whatsapp_lead` avec `dry_run=true` et la charge d'exemple de `tests/test_logic.py` : attendu `dry_run`, pipeline Séances, ad_id lu.
