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
