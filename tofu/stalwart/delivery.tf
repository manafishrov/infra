# Private relay listeners accept only identity-restricted edge traffic.
# LMTP serves recipient verification and the retiring edge's queue drain.
# Submission listeners retain their authentication requirements.
resource "stalwart_mta_stage_auth" "server" {
  require = {
    match = [{
      if   = "listener == 'edge-lmtp' || listener == 'smtp-edge' || listener == 'smtp-edge-local'"
      then = "false"
    }]
    else = "true"
  }
  sasl_mechanisms = {
    match = [
      {
        if   = "listener == 'edge-lmtp' || listener == 'smtp-edge' || listener == 'smtp-edge-local'"
        then = "false"
      },
      {
        if   = "local_port != 25 && is_tls"
        then = "[plain, login, oauthbearer, xoauth2]"
      },
      {
        if   = "local_port != 25"
        then = "[oauthbearer, xoauth2]"
      },
    ]
    else = "false"
  }
}

import {
  to = stalwart_mta_stage_auth.server
  id = "singleton"
}
