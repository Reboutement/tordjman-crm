"""Suivi des conversations WhatsApp : extrait l'attribution publicitaire (clic vers WhatsApp) d'un message
entrant. Sans dépendance à Frappe. Deux formes acceptées :
 1. la charge brute du webhook WhatsApp Cloud API de Meta (entry[].changes[].value.messages[].referral) ;
 2. une forme déjà normalisée (phone, referral, name, text), pour un relais (Chatwoot, n8n) qui l'a mise en forme.
Le bloc `referral` n'existe que sur le PREMIER message d'une conversation issue d'une pub « clic vers WhatsApp »
(champs Meta : source_id, source_type, source_url, headline, body, ctwa_clid). À vérifier sur un message réel
avant de s'y fier (voir docs/whatsapp-suivi.md)."""
import re

CHANNEL = "WhatsApp"


def normalize_phone(raw: str | None) -> str | None:
	digits = re.sub(r"\D", "", raw or "")
	return f"+{digits}" if 7 <= len(digits) <= 15 else None


def _from_cloud_api(payload: dict) -> list[dict]:
	out = []
	for entry in payload.get("entry") or []:
		for change in entry.get("changes") or []:
			value = change.get("value") or {}
			names = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts") or []}
			for msg in value.get("messages") or []:
				out.append({"phone": msg.get("from"), "name": names.get(msg.get("from")),
				            "text": (msg.get("text") or {}).get("body"), "referral": msg.get("referral") or {}})
	return out


def extract_events(payload: dict) -> list[dict]:
	"""Retourne des événements normalisés : phone (E.164), name, text, ad (dict d'attribution ou {})."""
	raw = _from_cloud_api(payload) if "entry" in payload else [payload]
	events = []
	for item in raw:
		phone = normalize_phone(item.get("phone"))
		if not phone:
			continue
		ref = item.get("referral") or {}
		ad = {}
		if ref.get("source_id"):
			ad = {"ad_id": str(ref["source_id"]), "click_id": ref.get("ctwa_clid"), "headline": ref.get("headline"),
			      "source_url": ref.get("source_url"), "source_type": ref.get("source_type")}
		events.append({"phone": phone, "name": item.get("name"), "text": item.get("text"), "ad": ad})
	return events
