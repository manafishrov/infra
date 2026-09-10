locals {
  mail_groups = {
    support  = "Support Mailbox"
    business = "Business Mailbox"
    accounts = "Accounts Mailbox"
    infra    = "Infrastructure Mailbox"
  }
}

resource "pocketid_group" "email_admin" {
  name          = "email-admin"
  friendly_name = "Email Administrators"
}

# Keep shared-mailbox membership independent of application authorization groups.
# Initial members are adopted from existing mail access; the provider's group
# resource does not manage membership, so it remains administered in Pocket ID.
resource "pocketid_group" "mail" {
  for_each = local.mail_groups

  name          = "mail-${each.key}"
  friendly_name = each.value
}

resource "pocketid_client" "stalwart" {
  # Public identifier, shared with the Stalwart configuration without a secret.
  client_id     = "stalwart"
  name          = "Stalwart"
  callback_urls = ["https://email.manafishrov.com/account/oauth/callback"]
  launch_url    = "https://email.manafishrov.com"
  is_public     = true
  pkce_enabled  = true
  allowed_user_groups = sort(concat(
    [for group in pocketid_group.mail : group.id],
    [pocketid_group.email_admin.id],
  ))
}

# Pocket ID uses a client's allowlist as the SCIM synchronization boundary.
# Keep that boundary mailbox-only even though the interactive OIDC client also
# authorizes administrators; the admin group must never become a mailbox.
resource "pocketid_client" "stalwart_scim" {
  client_id     = "stalwart-scim"
  name          = "Stalwart SCIM scope"
  callback_urls = ["https://backend.manafishrov.com/scim-unused"]
  is_public     = true
  pkce_enabled  = true
  allowed_user_groups = sort([
    for group in pocketid_group.mail : group.id
  ])
}

resource "pocketid_scim_service_provider" "stalwart" {
  client_id = pocketid_client.stalwart_scim.id
  endpoint  = "https://backend.manafishrov.com/scim/v2"
  token     = var.manafishrov_stalwart_scim_token
}
