# Recipient probes and final delivery share the edge's IP. Banning that IP
# after unknown recipients would let Internet senders disable all delivery.
# LMTP/24 remains identity-restricted. The new private PROXY SMTP listener
# restores real sender IPs but does not make shared LMTP probes safe to ban.
# HTTP authentication and scanner bans use the rightmost Gateway-appended
# X-Forwarded-For address (one trusted hop). SMTP PROXY trust stays scoped
# to smtp-edge; shared LMTP probes must still never trigger abuse bans.
resource "stalwart_security" "server" {
  abuse_ban_rate = null

  lifecycle {
    postcondition {
      condition     = self.abuse_ban_rate == null
      error_message = "Private LMTP must not ban the shared edge for recipient probes. The provider cannot clear this Optional+Computed value: apply the narrowly scoped native null update, then reconcile. This check detects drift; it does not repair it."
    }
  }
}

import {
  to = stalwart_security.server
  id = "singleton"
}
