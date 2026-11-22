# Adopt the existing production objects on the first apply. Import blocks are
# intentionally retained so rebuilding state cannot accidentally create
# duplicates with new server-assigned identifiers.
import {
  to = stalwart_tracer_stdout.stdout
  id = "jdzlxtbqarqa"
}
import {
  to = stalwart_mta_route_relay.mx
  id = "jdzlxtboapaa"
}
import {
  to = stalwart_application.webui
  id = "jecrqbfkabqa"
}
import {
  to = stalwart_directory_oidc.pocket_id
  id = "jdzlxs2sajaa"
}
import {
  to = stalwart_domain.manafishrov
  id = "c"
}
import {
  to = stalwart_domain.system
  id = "b"
}
import {
  to = stalwart_mailing_list.postmaster
  id = "b"
}
import {
  to = stalwart_certificate.wildcard
  id = "jdzlxs2saiaa"
}
import {
  to = stalwart_network_listener.https
  id = "jdzlxs2qahaa"
}
import {
  to = stalwart_network_listener.http
  id = "jdzlxs2qagaa"
}
import {
  to = stalwart_network_listener.sieve
  id = "jdzlxs2qafaa"
}
import {
  to = stalwart_network_listener.imaps
  id = "jdzlxs2qaeaa"
}
import {
  to = stalwart_network_listener.submission
  id = "jdzlxs2qadaa"
}
import {
  to = stalwart_network_listener.submissions
  id = "jdzlxs2qacaa"
}
import {
  to = stalwart_network_listener.edge_lmtp
  id = "jdzlxs2qabaa"
}
import {
  to = stalwart_authentication.this
  id = "singleton"
}
import {
  to = stalwart_system_settings.this
  id = "singleton"
}
import {
  to = stalwart_sender_auth.this
  id = "singleton"
}
import {
  to = stalwart_mta_stage_data.this
  id = "singleton"
}
import {
  to = stalwart_mta_sts.this
  id = "singleton"
}
import {
  to = stalwart_imap.this
  id = "singleton"
}

import {
  to = stalwart_http.server
  id = "singleton"
}

# Fresh state would otherwise plan creates for these existing listeners.
import {
  for_each = var.smtp_edge_activation_ready ? toset(["jfhnfsjeabqa"]) : toset([])
  to       = stalwart_network_listener.smtp_edge[0]
  id       = each.value
}

import {
  for_each = var.smtp_edge_activation_ready ? toset(["jfhnfsjeaaqa"]) : toset([])
  to       = stalwart_network_listener.smtp_edge_local[0]
  id       = each.value
}

import {
  to = stalwart_dkim_signature_dkim1_rsa_sha256.manafishrov
  id = "jdzlxs2ualqa"
}
import {
  to = stalwart_dkim_signature_dkim1_ed25519_sha256.manafishrov
  id = "jdzlxs2uamqa"
}

# The former DKIM publisher. Kept until the domain no longer links to it, since
# Stalwart refuses to delete a linked DNS server.
import {
  to = stalwart_dns_server_cloudflare.dkim
  id = "jfi2hgdoabaa"
}
