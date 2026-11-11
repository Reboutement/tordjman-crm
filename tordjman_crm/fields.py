"""Champs métier : le noyau de 14 champs validé le 2026-11-07, pris dans docs/crm-reference-for-tajfine.md
(« Intention » est la valeur canonique lue par les workflows), plus deux champs techniques. Aucun champ inventé. Les types sont des choix
raisonnables à valider contre GHL (la référence donne les rôles, pas les types). Sans dépendance à Frappe."""

PREFIX = "tj_"
INTENTION_VALUES = ("Private Session", "Training", "Workshop", "Hospitality Partner", "Partnership", "Other")

# (libellé GHL exact, type Frappe, options ou None, sensible)
# Noyau validé par le propriétaire le 2026-11-07 : 11 champs communs + 3 champs B2B. Les autres champs de
# la référence (qualification fine, webinaire, etc.) ne sont PAS créés : on les recrée si un process les réclame.
BUSINESS_FIELDS = (
	("Intention", "Select", "\n" + "\n".join(INTENTION_VALUES), False),
	("Main Objective", "Small Text", None, False),
	("Timing / Urgency", "Data", None, False),
	("Current Location", "Data", None, False),
	("Chosen Format", "Data", None, False),
	("Session Location Preference", "Data", None, False),
	("Pre-Session Notes", "Small Text", None, False),
	("Form Language", "Select", "\nfr\nes\nen", False),
	("Marketing Consent", "Check", None, False),
	("Known Contraindication", "Small Text", None, True),
	("Prior Experience", "Small Text", None, False),
	("Company / Establishment", "Data", None, False),
	("Establishment Type", "Data", None, False),
	("Role / Function", "Data", None, False),
)

# Champs techniques de rapprochement avec GHL (ne sont pas des champs métier GHL).
TECHNICAL_FIELDS = (
	("GHL Opportunity ID", "Data", None, False),
	("Source brute GHL", "Data", None, False),
	# Attribution publicitaire : renseignés par api.whatsapp_lead (clic vers WhatsApp) ou le formulaire du site.
	("Canal d'entree", "Data", None, False),
	("Pub Meta ID", "Data", None, False),
	("Clic pub ID", "Data", None, False),
	("Titre de la pub", "Data", None, False),
	("URL source", "Small Text", None, False),
)

# Tous les champs du noyau sont montrés dans le panneau latéral.
SIDE_PANEL = tuple(row[0] for row in BUSINESS_FIELDS)

# Champs de conservation GHL déjà présents sur Contact (créés le 28/10). Recréés seulement s'ils manquent.
CONTACT_CONSERVATION_FIELDS = (
	{"fieldname": "custom_ghl_section", "label": "Reprise GHL", "fieldtype": "Section Break", "collapsible": 1},
	{"fieldname": "custom_ghl_contact_id", "label": "GHL Contact ID", "fieldtype": "Data", "unique": 1, "read_only": 1},
	{"fieldname": "custom_ghl_source", "label": "GHL Source", "fieldtype": "Data", "read_only": 1},
	{"fieldname": "custom_ghl_created_at", "label": "GHL Created At", "fieldtype": "Datetime", "read_only": 1},
	{"fieldname": "custom_ghl_updated_at", "label": "GHL Updated At", "fieldtype": "Datetime", "read_only": 1},
	{"fieldname": "custom_ghl_first_attribution", "label": "GHL First Attribution", "fieldtype": "Long Text", "read_only": 1},
	{"fieldname": "custom_ghl_last_attribution", "label": "GHL Last Attribution", "fieldtype": "Long Text", "read_only": 1},
	{"fieldname": "custom_ghl_payload", "label": "GHL Payload", "fieldtype": "Long Text", "read_only": 1, "hidden": 1},
)


def fieldname(label: str) -> str:
	slug = "".join(c if c.isalnum() else "_" for c in label.lower())
	return PREFIX + "_".join(part for part in slug.split("_") if part)


def _definitions(rows) -> list[dict]:
	defs = []
	for label, fieldtype, options, sensitive in rows:
		d = {"fieldname": fieldname(label), "label": label, "fieldtype": fieldtype}
		if options:
			d["options"] = options
		if sensitive:
			d["description"] = "Donnée sensible : ne jamais l'envoyer aux plateformes publicitaires."
		defs.append(d)
	return defs


def definitions() -> list[dict]:
	"""Définitions à créer sur CRM Lead et CRM Deal, avec une section repliable en tête."""
	header = {"fieldname": "tj_section", "label": "Informations Tordjman", "fieldtype": "Section Break", "collapsible": 1}
	return [header, *_definitions(BUSINESS_FIELDS), *_definitions(TECHNICAL_FIELDS)]


def deal_only_definitions() -> list[dict]:
	from tordjman_crm.pipelines import PIPELINES
	return [{"fieldname": "tj_pipeline", "label": "Pipeline", "fieldtype": "Select",
	         "options": "\n" + "\n".join(PIPELINES),
	         "read_only": 1, "description": "Calculé depuis l'étape. Ne pas modifier à la main."}]


def side_panel_fieldnames() -> list[str]:
	return [fieldname(label) for label in SIDE_PANEL]
