"""Tests de la logique pure (sans Frappe) : python -m unittest discover -s . -t .. depuis tordjman_crm/."""
import re
import unittest
from pathlib import Path

from tordjman_crm import fields, pipelines, taxonomy, whatsapp

FIELD_TYPES = {"Data", "Small Text", "Long Text", "Int", "Check", "Date", "Datetime", "Select", "Section Break"}
REFERENCE = next((p / "docs" / "crm-reference-for-tajfine.md" for p in Path(__file__).resolve().parents
                  if (p / "docs" / "crm-reference-for-tajfine.md").exists()), None)


class TaxonomyTests(unittest.TestCase):
	def test_canonical_tags_are_accepted(self):
		for tag in taxonomy.CANONICAL_TAGS:
			self.assertTrue(taxonomy.check_tag(tag)[0], tag)

	def test_forbidden_and_dashed_variants_are_refused_with_a_suggestion(self):
		self.assertEqual(taxonomy.check_tag("intent-training"), (False, "Tag interdit : « intent-training »", "intent_training"))
		self.assertEqual(taxonomy.check_tag("intent training")[2], "intent_training")
		self.assertEqual(taxonomy.check_tag("segment-hotel")[2], "segment_hotel")
		self.assertFalse(taxonomy.check_tag("intent_mini_stage")[0])
		self.assertEqual(taxonomy.check_tag("Lang-FR")[2], "lang_fr")

	def test_the_dashed_exception_is_kept(self):
		self.assertTrue(taxonomy.check_tag("source-site-premium")[0])
		self.assertEqual(taxonomy.check_tag("source_site_premium")[2], "source-site-premium")

	def test_unknown_tags_are_left_alone(self):
		self.assertTrue(taxonomy.check_tag("ex_bdr_fup")[0])
		self.assertTrue(taxonomy.check_tag("geo_island_guadeloupe")[0])


class PipelineTests(unittest.TestCase):
	def test_status_names_are_unique_and_prefixed(self):
		names = [row["name"] for row in pipelines.all_statuses()]
		self.assertEqual(len(names), len(set(names)))
		for row in pipelines.all_statuses():
			self.assertTrue(row["name"].startswith(row["pipeline"] + pipelines.SEP))

	def test_every_pipeline_starts_open_and_types_are_valid(self):
		for name, stages in pipelines.PIPELINES.items():
			self.assertEqual(stages[0][1], "Open", name)
			for stage, typ, color in stages:
				self.assertIn(typ, {"Open", "Ongoing", "On Hold", "Won", "Lost"}, stage)
				self.assertIn(color, {"gray", "blue", "green", "red", "pink", "orange", "amber", "yellow", "cyan", "teal", "violet", "purple", "black"}, stage)

	def test_the_four_pipelines_wanted_by_the_owner(self):
		self.assertEqual(list(pipelines.PIPELINES), ["Prospection", "Séances", "Formation", "B2B"])
		self.assertEqual({k: len(v) for k, v in pipelines.PIPELINES.items()},
		                 {"Prospection": 6, "Séances": 5, "Formation": 5, "B2B": 5})

	def test_every_working_pipeline_ends_with_a_lost_stage(self):
		for name in ("Séances", "Formation", "B2B"):
			self.assertEqual(pipelines.PIPELINES[name][-1][1], "Lost", name)

	def test_the_pipeline_select_follows_the_pipelines(self):
		options = fields.deal_only_definitions()[0]["options"].split("\n")[1:]
		self.assertEqual(options, list(pipelines.PIPELINES))

	def test_routing(self):
		self.assertEqual(pipelines.route_pipeline("Private Session"), "Séances")
		self.assertEqual(pipelines.route_pipeline("Training"), "Formation")
		self.assertEqual(pipelines.route_pipeline("Partnership"), "B2B")
		self.assertEqual(pipelines.route_pipeline("Hospitality Partner"), "B2B")
		self.assertEqual(pipelines.route_pipeline("Other"), "Prospection")
		self.assertEqual(pipelines.route_pipeline(None, ["intent_private_session"]), "Séances")
		self.assertEqual(pipelines.route_pipeline(None, ["lang_fr"]), "Prospection")

	def test_conflicting_intents_go_to_human_review_not_to_two_pipelines(self):
		self.assertEqual(pipelines.route_pipeline(None, ["intent_training", "intent_private_session"]), "Prospection")

	def test_the_field_beats_the_tags(self):
		self.assertEqual(pipelines.route_pipeline("Training", ["intent_private_session"]), "Formation")

	def test_lookup_helpers(self):
		self.assertEqual(pipelines.first_status("Séances"), "Séances – Nouveau lead")
		self.assertEqual(pipelines.pipeline_of_status("Formation – Inscrit (paiement reçu)"), "Formation")
		self.assertIsNone(pipelines.pipeline_of_status("Won"))
		self.assertIsNone(pipelines.pipeline_of_status(None))


class FieldTests(unittest.TestCase):
	def test_fieldnames_are_unique_prefixed_and_short(self):
		names = [d["fieldname"] for d in fields.definitions() + fields.deal_only_definitions()]
		self.assertEqual(len(names), len(set(names)))
		for name in names:
			self.assertTrue(name.startswith("tj_"), name)
			self.assertLessEqual(len(name), 60, name)

	def test_types_are_known_and_selects_have_options(self):
		for d in fields.definitions() + fields.deal_only_definitions() + list(fields.CONTACT_CONSERVATION_FIELDS):
			self.assertIn(d["fieldtype"], FIELD_TYPES, d["fieldname"])
			if d["fieldtype"] == "Select":
				self.assertTrue(d["options"].startswith("\n"), d["fieldname"])

	def test_intention_values_are_exactly_the_six_documented_ones(self):
		self.assertEqual(fields.INTENTION_VALUES,
		                 ("Private Session", "Training", "Workshop", "Hospitality Partner", "Partnership", "Other"))

	def test_conservation_fields_keep_the_names_created_on_28_october(self):
		names = {d["fieldname"] for d in fields.CONTACT_CONSERVATION_FIELDS}
		self.assertTrue({"custom_ghl_contact_id", "custom_ghl_source", "custom_ghl_created_at", "custom_ghl_updated_at",
		                 "custom_ghl_first_attribution", "custom_ghl_last_attribution", "custom_ghl_payload"} <= names)

	def test_side_panel_fields_exist(self):
		defined = {d["fieldname"] for d in fields.definitions()}
		self.assertTrue(set(fields.side_panel_fieldnames()) <= defined)

	def test_the_core_is_exactly_the_fourteen_validated_fields(self):
		labels = [row[0] for row in fields.BUSINESS_FIELDS]
		self.assertEqual(len(labels), 14)
		self.assertEqual(labels[:11], ["Intention", "Main Objective", "Timing / Urgency", "Current Location", "Chosen Format",
		                              "Session Location Preference", "Pre-Session Notes", "Form Language", "Marketing Consent",
		                              "Known Contraindication", "Prior Experience"])
		self.assertEqual(labels[11:], ["Company / Establishment", "Establishment Type", "Role / Function"])
		for dropped in ("Qualification Score", "Webinar Date", "Main Obstacle", "Internal Notes", "Number of Participants"):
			self.assertNotIn(dropped, labels)

	@unittest.skipUnless(REFERENCE, "docs/crm-reference-for-tajfine.md introuvable")
	def test_every_label_comes_from_the_reference_document(self):
		text = REFERENCE.read_text(encoding="utf-8")
		block = re.search(r"## Existing GHL Fields\s+```text\n(.*?)```", text, re.S).group(1)
		documented = {line.strip() for line in block.splitlines() if line.strip()}
		self.assertTrue({row[0] for row in fields.BUSINESS_FIELDS} - {"Intention"} <= documented)


if __name__ == "__main__":
	unittest.main()


class WhatsappTests(unittest.TestCase):
	CLOUD = {"entry": [{"changes": [{"value": {
		"contacts": [{"wa_id": "33612345678", "profile": {"name": "Test"}}],
		"messages": [{"from": "33612345678", "text": {"body": "Bonjour"},
		              "referral": {"source_id": "120246537594180068", "ctwa_clid": "AbC", "headline": "Réservez", "source_type": "ad"}}]}}]}]}

	def test_cloud_api_referral_is_extracted(self):
		ev = whatsapp.extract_events(self.CLOUD)[0]
		self.assertEqual(ev["phone"], "+33612345678")
		self.assertEqual(ev["ad"]["ad_id"], "120246537594180068")
		self.assertEqual(ev["ad"]["click_id"], "AbC")

	def test_organic_message_has_no_ad(self):
		ev = whatsapp.extract_events({"phone": "0033 6 12 34 56 78", "text": "salut"})[0]
		self.assertEqual(ev["ad"], {})
		self.assertEqual(ev["phone"], "+0033612345678")

	def test_invalid_phone_is_skipped(self):
		self.assertEqual(whatsapp.extract_events({"phone": "abc"}), [])

	def test_ad_fields_are_ascii_frappe_fieldnames(self):
		names = [d["fieldname"] for d in fields.definitions()]
		for n in ("tj_canal_d_entree", "tj_pub_meta_id", "tj_clic_pub_id", "tj_titre_de_la_pub", "tj_url_source"):
			self.assertIn(n, names)
		self.assertTrue(all(n.isascii() for n in names))
