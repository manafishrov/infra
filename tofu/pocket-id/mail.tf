locals {
  mail_groups = {
    support  = "Support Mailbox"
    business = "Business Mailbox"
    accounts = "Accounts Mailbox"
    infra    = "Infrastructure Mailbox"
  }
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
  callback_urls = ["https://stalwart.manafishrov.com/oauth/callback"]
  # Add a launcher URL only after mailbox adoption and Stalwart OIDC activation.
  is_public    = true
  pkce_enabled = true
  allowed_user_groups = sort([
    for group in pocketid_group.mail : group.id
  ])
}

# Do not create a SCIM service-provider resource until all existing mailboxes
# have been imported and linked to the actual Pocket ID user/group identifiers.
