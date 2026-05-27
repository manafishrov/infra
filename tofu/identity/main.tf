resource "pocketid_group" "vaultwarden" {
  name          = "vaultwarden"
  friendly_name = "Vaultwarden Users"
}

resource "pocketid_client" "vaultwarden" {
  name                = "Vaultwarden"
  callback_urls       = ["https://vault.manafishrov.com/identity/connect/oidc-signin"]
  launch_url          = "https://vault.manafishrov.com"
  pkce_enabled        = true
  allowed_user_groups = [pocketid_group.vaultwarden.id]
}

resource "pocketid_group" "nextcloud" {
  name          = "nextcloud"
  friendly_name = "Nextcloud Users"
}

resource "pocketid_group" "admin" {
  name          = "admin"
  friendly_name = "Administrators"
}

resource "pocketid_group" "management" {
  name          = "management"
  friendly_name = "Management Team"
}

resource "pocketid_client" "nextcloud" {
  name          = "Nextcloud"
  callback_urls = ["https://cloud.manafishrov.com/apps/user_oidc/code"]
  launch_url    = "https://cloud.manafishrov.com"
  pkce_enabled  = true
  allowed_user_groups = [
    pocketid_group.nextcloud.id,
    pocketid_group.admin.id,
    pocketid_group.management.id,
  ]
}

resource "pocketid_group" "n8n" {
  name          = "n8n"
  friendly_name = "n8n Users"
}

resource "pocketid_client" "n8n" {
  name          = "n8n"
  callback_urls = ["https://n8n.manafishrov.com/oauth2/callback"]
  launch_url    = "https://n8n.manafishrov.com"
  pkce_enabled  = true
  allowed_user_groups = [
    pocketid_group.n8n.id,
    pocketid_group.admin.id,
  ]
}
