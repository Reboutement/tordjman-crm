"""API de double écriture : le site (/api/lead) envoie le lead ici APRÈS l'avoir écrit dans GHL.
GHL reste la source de vérité. Un échec ici ne doit jamais bloquer la capture côté GHL : l'appelant
journalise et réessaie (l'appel est idempotent). Désactivée par défaut. Dépend de Frappe ; non exécutée
dans la session qui l'a écrite : à tester sur une instance isolée avec des données fictives."""
import json

import frappe
from frappe import _

from tordjman_crm import fields as fieldmod
from tordjman_crm import pipelines, taxonomy, whatsapp

FLAG = "tordjman_dual_write_enabled"  # à poser dans site_config.json, absent = désactivé
ALLOWED_ROLES = ("Tordjman API", "System Manager")
BUSINESS_FIELDNAMES = {fieldmod.fieldname(row[0]) for row in fieldmod.BUSINESS_FIELDS}


def _as_dict(payload: str | dict) -> dict:
	data = json.loads(payload) if isinstance(payload, str) else payload
	if not isinstance(data, dict):
		frappe.throw(_("Charge utile invalide"))
	return data


def _find_contact(external_id: str | None, email: str | None) -> tuple[str | None, str | None]:
	"""Rapprochement : identifiant GHL d'abord, puis e-mail. Retourne (nom, conflit)."""
	by_id = frappe.db.get_value("Contact", {"custom_ghl_contact_id": external_id}, "name") if external_id else None
	by_email = frappe.db.get_value("Contact Email", {"email_id": email}, "parent") if email else None
	if by_id and by_email and by_id != by_email:
		return None, f"conflit : l'identifiant GHL pointe vers {by_id} et l'e-mail vers {by_email}"
	return by_id or by_email, None


@frappe.whitelist(methods=["POST"])
def create_lead(payload: str | dict, dry_run: bool = False) -> dict:
	"""Crée ou met à jour un contact et une opportunité. `dry_run` n'écrit rien."""
	frappe.only_for(ALLOWED_ROLES)
	data = _as_dict(payload)
	dry_run = frappe.parse_json(dry_run) if isinstance(dry_run, str) else bool(dry_run)

	tags = [t for t in (data.get("tags") or []) if isinstance(t, str)]
	bad = []
	for tag in tags:
		ok, _reason, suggestion = taxonomy.check_tag(tag)
		if not ok:
			bad.append((tag, suggestion))
	if bad:
		return {"status": "rejected", "reason": "tags non canoniques", "tags": bad}

	intention = data.get("intention")
	if intention and intention not in fieldmod.INTENTION_VALUES:
		return {"status": "rejected", "reason": f"intention inconnue : {intention}"}
	intent_tag = pipelines.tag_for_intention(intention)
	if intent_tag and intent_tag not in tags:
		tags.append(intent_tag)

	pipeline = pipelines.route_pipeline(intention, tags)
	status = pipelines.first_status(pipeline)

	email = (data.get("email") or "").strip().lower() or None
	external_id = data.get("external_id")
	contact_name, conflict = _find_contact(external_id, email)
	plan = {"pipeline": pipeline, "status": status, "tags": tags,
	        "contact": contact_name or "(à créer)", "dry_run": dry_run}
	if conflict:
		return {"status": "conflict", "reason": conflict, **plan}
	if dry_run:
		return {"status": "dry_run", **plan}
	if not frappe.conf.get(FLAG):
		return {"status": "disabled", "reason": f"{FLAG} n'est pas activé sur ce site", **plan}

	contact = _upsert_contact(contact_name, data, email, external_id)
	deal = _create_deal(contact, data, email, pipeline, status)
	for tag in tags:
		from frappe.desk.doctype.tag.tag import add_tag
		add_tag(tag, "CRM Deal", deal.name)
		add_tag(tag, "Contact", contact.name)
	if data.get("note"):
		frappe.get_doc({"doctype": "FCRM Note", "title": "Note du formulaire", "content": data["note"],
		                "reference_doctype": "CRM Deal", "reference_docname": deal.name}).insert(ignore_permissions=True)
	return {"status": "created" if not contact_name else "updated", "deal": deal.name, "contact": contact.name, **plan}


def _upsert_contact(name: str | None, data: dict, email: str | None, external_id: str | None):
	doc = frappe.get_doc("Contact", name) if name else frappe.new_doc("Contact")
	if not name:
		doc.first_name = data.get("first_name") or (email or "Contact")
		doc.last_name = data.get("last_name")
		if email:
			doc.append("email_ids", {"email_id": email, "is_primary": 1})
		if data.get("phone"):
			doc.append("phone_nos", {"phone": data["phone"], "is_primary_mobile_no": 1})
	if external_id and not doc.get("custom_ghl_contact_id"):
		doc.custom_ghl_contact_id = external_id
	if data.get("source"):
		doc.custom_ghl_source = data["source"]
	attribution = data.get("attribution") or {}
	if attribution.get("first") and not doc.get("custom_ghl_first_attribution"):
		doc.custom_ghl_first_attribution = json.dumps(attribution["first"], ensure_ascii=False)
	if attribution.get("last"):
		doc.custom_ghl_last_attribution = json.dumps(attribution["last"], ensure_ascii=False)
	doc.flags.ignore_permissions = True
	if name:
		doc.save()
	else:
		doc.insert()
	return doc


def _create_deal(contact, data: dict, email: str | None, pipeline: str, status: str):
	values = {k: v for k, v in (data.get("fields") or {}).items() if k in BUSINESS_FIELDNAMES}
	values["tj_intention"] = data.get("intention") or values.get("tj_intention")
	deal = frappe.get_doc({
		"doctype": "CRM Deal", "status": status, "tj_pipeline": pipeline,
		"first_name": contact.first_name, "last_name": contact.last_name, "email": email,
		"mobile_no": data.get("phone"), "tj_ghl_opportunity_id": data.get("ghl_opportunity_id"),
		"tj_source_brute_ghl": data.get("source"), **{k: v for k, v in values.items() if v is not None},
	})
	deal.append("contacts", {"contact": contact.name, "is_primary": 1})
	deal.flags.ignore_permissions = True
	deal.insert()
	return deal


@frappe.whitelist(methods=["POST"])
def whatsapp_lead(payload: str | dict, dry_run: bool = False, pipeline: str = "Séances") -> dict:
	"""Suivi WhatsApp : pour chaque premier message, crée (ou retrouve) le contact par téléphone et une
	opportunité portant l'identifiant de la pub Meta. Un message sans bloc `referral` (conversation organique)
	est enregistré sans pub, pour ne pas perdre le lead. Idempotent : même téléphone + même pub = pas de doublon."""
	frappe.only_for(ALLOWED_ROLES)
	data = _as_dict(payload)
	dry_run = frappe.parse_json(dry_run) if isinstance(dry_run, str) else bool(dry_run)
	if pipeline not in pipelines.PIPELINES:
		return {"status": "rejected", "reason": f"pipeline inconnu : {pipeline}"}
	events = whatsapp.extract_events(data)
	if not events:
		return {"status": "ignored", "reason": "aucun message avec un numéro valide", "results": []}
	status = pipelines.first_status(pipeline)
	results = []
	for ev in events:
		ad = ev["ad"]
		existing = frappe.db.get_value("CRM Deal", {"mobile_no": ev["phone"], "tj_pub_meta_id": ad.get("ad_id") or ["is", "not set"]}, "name")
		plan = {"phone": ev["phone"], "ad_id": ad.get("ad_id"), "pipeline": pipeline, "status": status}
		if existing:
			results.append({"status": "duplicate", "deal": existing, **plan})
		elif dry_run:
			results.append({"status": "dry_run", **plan})
		elif not frappe.conf.get(FLAG):
			results.append({"status": "disabled", "reason": f"{FLAG} n'est pas activé sur ce site", **plan})
		else:
			contact_name = frappe.db.get_value("Contact Phone", {"phone": ev["phone"]}, "parent")
			contact = _upsert_contact(contact_name, {"first_name": ev["name"] or ev["phone"], "phone": ev["phone"],
			                                         "source": "WhatsApp" + (" (pub Meta)" if ad else "")}, None, None)
			deal = frappe.get_doc({
				"doctype": "CRM Deal", "status": status, "tj_pipeline": pipeline, "first_name": contact.first_name,
				"mobile_no": ev["phone"], "tj_canal_d_entree": whatsapp.CHANNEL, "tj_pub_meta_id": ad.get("ad_id"),
				"tj_clic_pub_id": ad.get("click_id"), "tj_titre_de_la_pub": ad.get("headline"),
				"tj_url_source": ad.get("source_url"),
			})
			deal.append("contacts", {"contact": contact.name, "is_primary": 1})
			deal.flags.ignore_permissions = True
			deal.insert()
			results.append({"status": "created", "deal": deal.name, "contact": contact.name, **plan})
	return {"status": "ok", "results": results}
