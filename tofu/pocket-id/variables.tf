variable "manafishrov_pocketid_api_token" {
  type      = string
  sensitive = true
}

variable "manafishrov_stalwart_scim_token" {
  type      = string
  sensitive = true
}

# Retained during the additive secret rollout so the prior revision keeps its
# original password until host/user/password change in one controller apply.
variable "manafishrov_pocketid_smtp_password" {
  type      = string
  sensitive = true
  default   = null
}

variable "manafishrov_pocketid_resend_smtp_password" {
  description = "Resend API key for Pocket ID recovery email over implicit TLS"
  type        = string
  sensitive   = true
}
