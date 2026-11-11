"""Installation et mise en conformité, idempotentes : tout est créé s'il manque, jamais supprimé ni renommé.
Dépend de Frappe. Non exécuté dans la session qui l'a écrit : à tester sur une instance isolée."""
import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from tordjman_crm import fields, pipelines, taxonomy

API_ROLE = "Tordjman API"
LAYOUT_SECTION = "tj_section"


def after_install():
	ensure_all()


def after_migrate():
	ensure_all()


def ensure_all():
	ensure_role()
	ensure_statuses()
	ensure_tags()
	ensure_custom_fields()
	ensure_side_panels()
	frappe.db.commit()


def ensure_role():
	if not frappe.db.exists("Role", API_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": API_ROLE, "desk_access": 0}).insert(ignore_permissions=True)


def ensure_statuses():
	for row in pipelines.all_statuses():
		if frappe.db.exists("CRM Deal Status", row["name"]):
			continue
		doc = frappe.new_doc("CRM Deal Status")
		doc.deal_status = row["name"]
		doc.color = row["color"]
		doc.type = row["type"]
		doc.position = row["position"]
		doc.insert(ignore_permissions=True)


def ensure_tags():
	for name in taxonomy.CANONICAL_TAGS:
		if not frappe.db.exists("Tag", name):
			frappe.get_doc({"doctype": "Tag", "name": name}).insert(ignore_permissions=True)


def _missing(doctype: str, defs: list[dict]) -> list[dict]:
	meta = frappe.get_meta(doctype)
	missing = [d for d in defs if not meta.has_field(d["fieldname"])]
	previous = None
	for d in missing:
		d["insert_after"] = previous or ("source" if doctype in ("CRM Lead", "CRM Deal") else "")
		previous = d["fieldname"]
	return missing


def ensure_custom_fields():
	custom = {}
	for doctype in ("CRM Lead", "CRM Deal"):
		defs = fields.definitions() + (fields.deal_only_definitions() if doctype == "CRM Deal" else [])
		custom[doctype] = _missing(doctype, defs)
	custom["Contact"] = _missing("Contact", [dict(d) for d in fields.CONTACT_CONSERVATION_FIELDS])
	custom = {dt: defs for dt, defs in custom.items() if defs}
	if custom:
		create_custom_fields(custom)
		for doctype in custom:
			frappe.clear_cache(doctype=doctype)


def ensure_side_panels():
	"""Ajoute une section « Informations Tordjman » aux panneaux latéraux s'ils existent et ne l'ont pas."""
	wanted = fields.side_panel_fieldnames()
	for doctype in ("CRM Lead", "CRM Deal"):
		name = f"{doctype}-Side Panel"
		if not frappe.db.exists("CRM Fields Layout", name):
			continue
		layout = frappe.get_doc("CRM Fields Layout", name)
		sections = json.loads(layout.layout or "[]")
		flat = sections if not (sections and "sections" in sections[0]) else sections[0]["sections"]
		if any(s.get("name") == LAYOUT_SECTION for s in flat):
			continue
		flat.append({"label": "Informations Tordjman", "name": LAYOUT_SECTION, "opened": False,
		             "columns": [{"name": "tj_column", "fields": wanted}]})
		layout.layout = json.dumps(sections)
		layout.save(ignore_permissions=True)
