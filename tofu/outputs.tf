output "vaultwarden_pocketid_client_id" {
  value = pocketid_client.vaultwarden.client_id
}

output "vaultwarden_pocketid_client_secret" {
  value     = pocketid_client.vaultwarden.client_secret
  sensitive = true
}
