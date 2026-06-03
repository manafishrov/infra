variable "dkim_rsa_pub_manafishrov" {
  description = "Base64-encoded RSA DKIM public key for manafishrov.com (TXT record value, without the v=DKIM1; k=rsa; p= prefix)."
  type        = string
}

variable "dkim_ed25519_pub_manafishrov" {
  description = "Base64-encoded ed25519 DKIM public key for manafishrov.com (RFC 8463 raw 32-byte form)."
  type        = string
}

variable "mta_sts_id_manafishrov" {
  description = "MTA-STS policy id (bump to roll a new policy version)."
  type        = string
  default     = "v1"
}
