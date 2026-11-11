"""Tags canoniques et règles d'orthographe. Source : docs/crm-reference-for-tajfine.md. Sans dépendance à Frappe."""

# Orthographe exacte, avec les underscores. `source-site-premium` est la seule exception à tirets.
CANONICAL_TAGS = (
	"source-site-premium",
	"intent_training",
	"intent_private_session",
	"intent_partnership",
	"status_prospect",
	"status_customer",
	"priority_cold",
	"priority_warm",
	"priority_hot",
	"lang_fr",
	"lang_es",
	"lang_en",
	"campaign_hotels_resorts",
	"campaign_training",
	"campaign_private_sessions",
	"campaign_spas_institutes",
	"geo_country_mexique",
	"geo_city_mexico_city",
	"segment_hotel",
	"segment_villa",
	"segment_spa",
	"segment_praticien",
	"human_takeover_needed",
)

# Écritures explicitement interdites par la référence.
FORBIDDEN_TAGS = (
	"intent-training",
	"intent training",
	"segment-hotel",
	"intent_mini_stage",
)

INTENT_TAGS = ("intent_training", "intent_private_session", "intent_partnership")


def _norm(name: str) -> str:
	return name.strip().lower().replace("-", "_").replace(" ", "_")


_CANON_BY_NORM = {_norm(tag): tag for tag in CANONICAL_TAGS}


def check_tag(name: str) -> tuple[bool, str, str | None]:
	"""Retourne (ok, raison, suggestion). Un tag inconnu mais non ambigu reste accepté : seuls les tags
	interdits et les variantes à tiret ou à espace d'un tag canonique sont refusés."""
	if name in FORBIDDEN_TAGS:
		canon = _CANON_BY_NORM.get(_norm(name))
		return False, f"Tag interdit : « {name} »", canon
	canon = _CANON_BY_NORM.get(_norm(name))
	if canon and name != canon:
		return False, f"Écriture non canonique : « {name} »", canon
	return True, "", None
