"""Les quatre pipelines voulus par le propriétaire (2026-11-07) : Prospection, Séances, Formation, B2B.
Pipelines et étapes. Frappe CRM n'a pas d'objet pipeline : chaque étape est un « CRM Deal Status » dont le
nom est « <Pipeline> – <Étape> » (tiret demi-cadratin, convention déjà présente sur les préproductions).
Prospection reprend les étapes de GHL du 2026-11-01 ; les trois autres sont une proposition simplifiée (à valider). Sans dépendance à Frappe."""

SEP = " – "

# (étape, type Frappe CRM, couleur Frappe CRM). Les types Won / Lost / On Hold sont des hypothèses à valider.
PIPELINES: dict[str, tuple[tuple[str, str, str], ...]] = {
	"Prospection": (
		("Nouveau", "Open", "gray"),
		("À qualifier", "Open", "gray"),
		("Contacté", "Ongoing", "orange"),
		("Intérêt identifié", "Ongoing", "blue"),
		("À relancer", "Ongoing", "yellow"),
		("Non pertinent / Perdu", "Lost", "red"),
	),
	"Séances": (
		("Nouveau lead", "Open", "gray"),
		("RDV proposé", "Ongoing", "blue"),
		("RDV confirmé", "Ongoing", "green"),
		("Séance réalisée", "Won", "teal"),
		("Perdu / sans suite", "Lost", "red"),
	),
	"Formation": (
		("Nouveau", "Open", "gray"),
		("RDV pédagogique confirmé", "Ongoing", "green"),
		("Conseil donné", "Ongoing", "blue"),
		("Inscrit (paiement reçu)", "Won", "teal"),
		("Perdu / sans suite", "Lost", "red"),
	),
	"B2B": (
		("Nouveau contact pro", "Open", "gray"),
		("Échange en cours", "Ongoing", "orange"),
		("Devis envoyé", "Ongoing", "blue"),
		("Intervention validée", "Won", "green"),
		("Perdu / sans suite", "Lost", "red"),
	),
}

# Intention (valeur du champ) -> tag d'intention. Seules les trois premières lignes sont documentées ;
# Workshop et Hospitality Partner sont des hypothèses (à valider par le propriétaire).
INTENTION_TO_TAG = {
	"Private Session": "intent_private_session",
	"Training": "intent_training",
	"Workshop": "intent_training",  # hypothèse
	"Hospitality Partner": "intent_partnership",
	"Partnership": "intent_partnership",
	"Other": None,
}

TAG_TO_PIPELINE = {
	"intent_private_session": "Séances",
	"intent_training": "Formation",
	"intent_partnership": "B2B",
}

DEFAULT_PIPELINE = "Prospection"


def status_name(pipeline: str, stage: str) -> str:
	return f"{pipeline}{SEP}{stage}"


def all_statuses() -> list[dict]:
	rows = []
	for pipeline, stages in PIPELINES.items():
		for position, (stage, typ, color) in enumerate(stages, start=1):
			rows.append(
				{"name": status_name(pipeline, stage), "pipeline": pipeline, "stage": stage,
				 "type": typ, "color": color, "position": position}
			)
	return rows


_BY_NAME = {row["name"]: row for row in all_statuses()}


def pipeline_of_status(status: str | None) -> str | None:
	row = _BY_NAME.get(status or "")
	return row["pipeline"] if row else None


def first_status(pipeline: str) -> str:
	return status_name(pipeline, PIPELINES[pipeline][0][0])


def route_pipeline(intention: str | None, tags: list[str] | tuple[str, ...] = ()) -> str:
	"""Un contact ne reste jamais dans deux pipelines : l'intention du formulaire décide ; sinon les tags
	d'intention, s'il n'y en a qu'un ; en cas de conflit ou d'absence, Prospection (revue humaine)."""
	via_field = INTENTION_TO_TAG.get(intention or "")
	if via_field:
		return TAG_TO_PIPELINE[via_field]
	intents = {t for t in tags if t in TAG_TO_PIPELINE}
	if len(intents) == 1:
		return TAG_TO_PIPELINE[next(iter(intents))]
	return DEFAULT_PIPELINE


def tag_for_intention(intention: str | None) -> str | None:
	return INTENTION_TO_TAG.get(intention or "")
