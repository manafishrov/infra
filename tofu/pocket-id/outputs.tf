output "manafishrov_vaultwarden_pocketid_client_id" {
  value = pocketid_client.vaultwarden.id
}

output "manafishrov_vaultwarden_pocketid_client_secret" {
  value     = pocketid_client.vaultwarden.client_secret
  sensitive = true
}

output "manafishrov_nextcloud_pocketid_client_id" {
  value = pocketid_client.nextcloud.id
}

output "manafishrov_nextcloud_pocketid_client_secret" {
  value     = pocketid_client.nextcloud.client_secret
  sensitive = true
}

output "manafishrov_n8n_pocketid_client_id" {
  value = pocketid_client.n8n.id
}

output "manafishrov_n8n_pocketid_client_secret" {
  value     = pocketid_client.n8n.client_secret
  sensitive = true
}

output "manafishrov_roundcube_pocketid_client_id" {
  value = pocketid_client.roundcube.id
}

output "manafishrov_roundcube_pocketid_client_secret" {
  value     = pocketid_client.roundcube.client_secret
  sensitive = true
}

output "manafishrov_twenty_pocketid_client_id" {
  value = pocketid_client.twenty.id
}

output "manafishrov_twenty_pocketid_client_secret" {
  value     = pocketid_client.twenty.client_secret
  sensitive = true
}
