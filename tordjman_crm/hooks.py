app_name = "tordjman_crm"
app_title = "Tordjman CRM"
app_publisher = "Reboutement et Massage"
app_description = "Pipelines, champs, tags et API de double écriture pour Frappe CRM"
app_email = "contact@formationreboutement.fr"
app_license = "Proprietary"

required_apps = ["frappe", "crm"]

after_install = "tordjman_crm.install.after_install"
# Rejoue, sans rien supprimer ni renommer, ce que l'app doit garantir : statuts, champs, tags.
after_migrate = ["tordjman_crm.install.after_migrate"]

doc_events = {
	"CRM Deal": {"validate": "tordjman_crm.events.validate_deal"},
	"Tag": {"validate": "tordjman_crm.events.validate_tag"},  # après le nommage : le nom est connu
}
