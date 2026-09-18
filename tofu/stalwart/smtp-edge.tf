# Postfix forwards protected queue IP/EHLO attributes, not message headers.
# PROXY is accepted ONLY on this listener. The Cilium namespace+app identity
# rule is the trust boundary; pod IPs are not stable identities.
resource "stalwart_network_listener" "smtp_edge" {
  count = var.smtp_edge_activation_ready ? 1 : 0

  name                            = "smtp-edge"
  protocol                        = "smtp"
  bind                            = ["[::]:25"]
  use_tls                         = true
  tls_implicit                    = false
  override_proxy_trusted_networks = var.smtp_edge_proxy_networks
  depends_on = [
    stalwart_mta_stage_auth.server,
    stalwart_mta_stage_data.this,
    stalwart_sender_auth.this,
    stalwart_mta_stage_rcpt.server,
    stalwart_mta_stage_ehlo.server,
  ]
}

# Postfix-generated mail has no original SMTP client. Keep that path separate
# rather than inventing an Internet source IP or weakening the PROXY listener.
resource "stalwart_network_listener" "smtp_edge_local" {
  count = var.smtp_edge_activation_ready ? 1 : 0

  name                            = "smtp-edge-local"
  protocol                        = "smtp"
  bind                            = ["[::]:26"]
  use_tls                         = true
  tls_implicit                    = false
  override_proxy_trusted_networks = []
  depends_on = [
    stalwart_mta_stage_auth.server,
    stalwart_mta_stage_data.this,
    stalwart_sender_auth.this,
    stalwart_mta_stage_rcpt.server,
    stalwart_mta_stage_ehlo.server,
  ]
}

# A queued original EHLO need not be an FQDN. Keep the native port-25 default
# for any other listener; require/script remain imported Optional+Computed.
resource "stalwart_mta_stage_ehlo" "server" {
  reject_non_fqdn = {
    match = [{
      if   = "listener == 'edge-lmtp' || listener == 'smtp-edge' || listener == 'smtp-edge-local'"
      then = "false"
    }]
    else = "local_port == 25"
  }
}

import {
  to = stalwart_mta_stage_ehlo.server
  id = "singleton"
}
