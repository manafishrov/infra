# The private LMTP listener accepts final delivery from the ingress pod.
# Network policy limits that listener to trusted mail backends. Submission
# listeners retain their normal authentication requirements and mechanisms.
resource "stalwart_mta_stage_auth" "server" {
  require = {
    match = [{
      if   = "listener == 'edge-lmtp'"
      then = "false"
    }]
    else = "local_port != 25"
  }
  sasl_mechanisms = {
    match = [
      {
        if   = "listener == 'edge-lmtp'"
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
