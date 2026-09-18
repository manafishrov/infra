# Native Stalwart owns the existing keys. Never destroy them on handoff.
removed {
  from = stalwart_dkim_signature_dkim1_rsa_sha256.manafishrov
  lifecycle {
    destroy = false
  }
}

removed {
  from = stalwart_dkim_signature_dkim1_ed25519_sha256.manafishrov
  lifecycle {
    destroy = false
  }
}
