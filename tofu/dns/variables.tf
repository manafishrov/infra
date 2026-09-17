variable "dkim_rsa_pub_manafishrov" {
  description = "Base64-encoded RSA DKIM public key for manafishrov.com (the p= value only; no DKIM tags)."
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9+/]+={0,2}$", var.dkim_rsa_pub_manafishrov)) && length(var.dkim_rsa_pub_manafishrov) % 4 == 0
    error_message = "The DKIM public key must be single-line standard base64 without TXT quotes or tags."
  }
}

variable "dkim_ed25519_pub_manafishrov" {
  description = "Base64-encoded ed25519 DKIM public key for manafishrov.com (RFC 8463 raw 32-byte form)."
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9+/]+={0,2}$", var.dkim_ed25519_pub_manafishrov)) && length(var.dkim_ed25519_pub_manafishrov) % 4 == 0
    error_message = "The DKIM public key must be single-line standard base64 without TXT quotes or tags."
  }
}

variable "mta_sts_id_manafishrov" {
  description = "MTA-STS policy id (bump to roll a new policy version)."
  type        = string
  default     = "v1"
}
