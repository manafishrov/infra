variable "manafishrov_pocketid_api_token" {
  type      = string
  sensitive = true
}

variable "manafishrov_stalwart_scim_token" {
  type      = string
  sensitive = true
}

variable "manafishrov_pocketid_smtp_password" {
  description = "Resend API key for Pocket ID recovery email over implicit TLS"
  type        = string
  sensitive   = true
}
