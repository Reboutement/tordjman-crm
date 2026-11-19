"""Import des contacts GHL (export CSV) dans Frappe. Logique pure d'abord, accès Frappe ensuite.
Idempotent : la clé est custom_ghl_contact_id. Les tags GHL sont ramenés à l'orthographe canonique (les variantes à
tiret seraient refusées par le contrôle des tags). Les désabonnés e-mail et les « ne pas déranger » doivent être
fournis à part (ils ne figurent pas dans l'export) et ne doivent JAMAIS être perdus avant tout envoi."""
import csv
import io
import re
from datetime import datetime

from tordjman_crm import taxonomy

DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M",
                "%b %d %Y %I:%M %p", "%d/%m/%Y %H:%M", "%d/%m/%Y")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def parse_date(text):
	text = (text or "").strip()
	for fmt in DATE_FORMATS:
		try:
			return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
		except ValueError:
			continue
	return None


def normalize_phone(raw):
	digits = re.sub(r"\D", "", raw or "")
	return f"+{digits}" if 7 <= len(digits) <= 15 else None


def normalize_tags(raw):
	"""Retourne (tags_retenus, tags_écartés). Variante à tiret -> forme canonique ; interdit sans équivalent -> écarté."""
	kept, dropped = [], []
	for tag in (t.strip() for t in (raw or "").split(",")):
		if not tag:
			continue
		ok, _reason, suggestion = taxonomy.check_tag(tag)
		final = tag if ok else suggestion
		if final and final not in kept:
			kept.append(final)
		elif not final:
			dropped.append(tag)
	return kept, dropped


def parse_row(row):
	"""Une ligne de l'export GHL -> contact normalisé, ou None si inutilisable (ni e-mail ni téléphone, ni identifiant)."""
	ghl_id = (row.get("Contact Id") or "").strip()
	email = (row.get("Email") or "").strip().lower()
	email = email if EMAIL_RE.match(email) else None
	phone = normalize_phone(row.get("Phone"))
	if not ghl_id or not (email or phone):
		return None
	first = (row.get("First Name") or "").strip()
	last = (row.get("Last Name") or "").strip()
	if not first:
		first, last = (last or email or phone), ""
	tags, dropped = normalize_tags(row.get("Tags"))
	return {"ghl_id": ghl_id, "first_name": first, "last_name": last, "email": email, "phone": phone,
	        "source": (row.get("Source") or "").strip() or None, "created": parse_date(row.get("Created")),
	        "updated": parse_date(row.get("Last Activity")), "company": (row.get("Business Name") or "").strip() or None,
	        "tags": tags, "dropped_tags": dropped}


def read_export(text):
	"""Lit le CSV complet. Retourne (contacts, ignorés). Un identifiant GHL en double est ignoré."""
	contacts, skipped, seen = [], 0, set()
	for row in csv.DictReader(io.StringIO(text)):
		parsed = parse_row(row)
		if not parsed or parsed["ghl_id"] in seen:
			skipped += 1
			continue
		seen.add(parsed["ghl_id"])
		contacts.append(parsed)
	return contacts, skipped


def summarize(contacts, skipped, email_dnd_ids=()):
	dnd = set(email_dnd_ids)
	return {"contacts": len(contacts), "ignores": skipped, "avec_email": sum(1 for c in contacts if c["email"]),
	        "avec_telephone": sum(1 for c in contacts if c["phone"]),
	        "avec_tags": sum(1 for c in contacts if c["tags"]),
	        "tags_ecartes": sorted({t for c in contacts for t in c["dropped_tags"]}),
	        "desabonnes_email": sum(1 for c in contacts if c["ghl_id"] in dnd)}


def run(file_path, email_dnd_file=None, dry_run=True, limit=0):
	"""Point d'entrée : bench --site <site> execute tordjman_crm.ghl_import.run --kwargs '{"file_path": "...", "dry_run": true}'.
	file_path : fichier du site (dossier private/files) ou chemin absolu. Sans effet d'écriture si dry_run."""
	import frappe
	from frappe.desk.doctype.tag.tag import add_tag

	def _read(path):
		return frappe.get_doc("File", {"file_url": path}).get_content() if path.startswith("/private/") or path.startswith("/files/") \
			else open(path, encoding="utf-8-sig").read()

	text = _read(file_path)
	text = text.decode("utf-8-sig") if isinstance(text, bytes) else text
	contacts, skipped = read_export(text)
	dnd_ids = set()
	if email_dnd_file:
		dtext = _read(email_dnd_file)
		dtext = dtext.decode("utf-8-sig") if isinstance(dtext, bytes) else dtext
		dnd_ids = {(r.get("Contact Id") or "").strip() for r in csv.DictReader(io.StringIO(dtext))}
	if limit:
		contacts = contacts[:limit]
	report = summarize(contacts, skipped, dnd_ids)
	existing = set(frappe.get_all("Contact", filters={"custom_ghl_contact_id": ["in", [c["ghl_id"] for c in contacts]]},
	                              pluck="custom_ghl_contact_id")) if contacts else set()
	report["deja_presents"] = len(existing)
	if dry_run:
		return {"dry_run": True, **report}
	has_unsub = frappe.get_meta("Contact").has_field("unsubscribed")
	created = 0
	for i, c in enumerate(contacts, 1):
		if c["ghl_id"] in existing:
			continue
		doc = frappe.new_doc("Contact")
		doc.first_name, doc.last_name, doc.company_name = c["first_name"], c["last_name"], c["company"]
		doc.custom_ghl_contact_id, doc.custom_ghl_source = c["ghl_id"], c["source"]
		doc.custom_ghl_created_at, doc.custom_ghl_updated_at = c["created"], c["updated"]
		if c["email"]:
			doc.append("email_ids", {"email_id": c["email"], "is_primary": 1})
		if c["phone"]:
			doc.append("phone_nos", {"phone": c["phone"], "is_primary_mobile_no": 1})
		if has_unsub and c["ghl_id"] in dnd_ids:
			doc.unsubscribed = 1
		doc.flags.ignore_permissions = True
		doc.insert()
		for tag in c["tags"] + (["email_dnd"] if (c["ghl_id"] in dnd_ids and not has_unsub) else []):
			add_tag(tag, "Contact", doc.name)
		created += 1
		if i % 200 == 0:
			frappe.db.commit()
	frappe.db.commit()
	return {"dry_run": False, "crees": created, **report}
