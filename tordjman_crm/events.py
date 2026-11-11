"""Événements de documents. Dépend de Frappe."""
import frappe

from tordjman_crm.pipelines import pipeline_of_status
from tordjman_crm.taxonomy import check_tag


def validate_deal(doc, method=None):
	"""Garde `tj_pipeline` cohérent avec l'étape. Les étapes standard de Frappe CRM restent intactes."""
	pipeline = pipeline_of_status(doc.get("status"))
	if pipeline and doc.meta.has_field("tj_pipeline"):
		doc.tj_pipeline = pipeline


def validate_tag(doc, method=None):
	ok, reason, suggestion = check_tag(doc.name)
	if not ok:
		hint = f" Utiliser « {suggestion} »." if suggestion else ""
		frappe.throw(reason + "." + hint, title="Tag non canonique")
