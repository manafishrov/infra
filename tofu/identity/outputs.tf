output "vaultwarden_pocketid_client_id" {
  value = pocketid_client.vaultwarden.id
}

output "vaultwarden_pocketid_client_secret" {
  value     = pocketid_client.vaultwarden.client_secret
  sensitive = true
}

output "nextcloud_pocketid_client_id" {
  value = pocketid_client.nextcloud.id
}

output "nextcloud_pocketid_client_secret" {
  value     = pocketid_client.nextcloud.client_secret
  sensitive = true
}
