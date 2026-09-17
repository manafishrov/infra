# Private LMTP recipient probes must receive the native negative response before
# the edge's deadline. Keep the public/authenticated listener penalty unchanged.
resource "stalwart_mta_stage_rcpt" "server" {
  wait_on_fail = {
    match = [{
      if   = "listener == 'edge-lmtp'"
      then = "0ms"
    }]
    else = "5s"
  }
}

import {
  to = stalwart_mta_stage_rcpt.server
  id = "singleton"
}
