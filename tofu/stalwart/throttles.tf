# LMTP is reachable only from trusted ingress. Its shared source addresses and
# recipient probes must not consume public-client limits or stall final mail.
# Preserve both existing limits for every non-LMTP listener.
resource "stalwart_mta_inbound_throttle" "sender_recipient" {
  description = "Sender address to recipient throttle"
  enable      = true
  key         = ["senderDomain", "rcpt"]
  match       = { else = "listener != 'edge-lmtp'", match = [] }
  rate        = { count = 25, period = 3600000 }
}

resource "stalwart_mta_inbound_throttle" "sender_ip" {
  description = "Sender IP throttle"
  enable      = true
  key         = ["remoteIp"]
  match       = { else = "listener != 'edge-lmtp'", match = [] }
  rate        = { count = 5, period = 1000 }
}

import {
  to = stalwart_mta_inbound_throttle.sender_recipient
  id = "jdzlxxlsacab"
}

import {
  to = stalwart_mta_inbound_throttle.sender_ip
  id = "jdzlxxlsabab"
}
