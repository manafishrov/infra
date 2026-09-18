# Move only these instances to unkeyed addresses, then forget without deleting.
# OpenTofu 1.11.5 does not accept instance keys directly in removed.from.

moved {
  from = cloudflare_dns_record.manafishrov["stalwart_dkim_rsa"]
  to   = cloudflare_dns_record.stalwart_dkim_rsa_handoff
}

removed {
  from = cloudflare_dns_record.stalwart_dkim_rsa_handoff
  lifecycle {
    destroy = false
  }
}

moved {
  from = cloudflare_dns_record.manafishrov["stalwart_dkim_ed25519"]
  to   = cloudflare_dns_record.stalwart_dkim_ed25519_handoff
}

removed {
  from = cloudflare_dns_record.stalwart_dkim_ed25519_handoff
  lifecycle {
    destroy = false
  }
}
