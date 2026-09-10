# __generated__ by OpenTofu from "singleton"
resource "stalwart_mta_sts" "this" {
  max_age  = 604800000
  mode     = "testing"
  mx_hosts = null
}

# __generated__ by OpenTofu from "singleton"
resource "stalwart_authentication" "this" {
  default_admin_role_ids  = ["b", "e"]
  default_group_role_ids  = ["c"]
  default_tenant_role_ids = ["b", "d"]
  default_user_role_ids   = ["b"]
  directory_id            = stalwart_directory_oidc.pocket_id.id
  max_api_keys            = 5
  max_app_passwords       = 5
  password_default_expiry = null
  password_hash_algorithm = "argon2id"
  password_max_length     = 128
  password_min_length     = 8
  password_min_strength   = "three"
}

# __generated__ by OpenTofu from "jdzlxs2sajaa"
resource "stalwart_directory_oidc" "pocket_id" {
  claim_groups     = null
  claim_name       = "name"
  claim_username   = "email"
  description      = "Pocket ID for manafishrov.com"
  issuer_url       = "https://id.manafishrov.com"
  member_tenant_id = null
  require_audience = "stalwart"
  require_scopes   = ["email", "openid"]
  username_domain  = "manafishrov.com"
}

# __generated__ by OpenTofu from "b"
resource "stalwart_mailing_list" "postmaster" {
  aliases          = null
  description      = null
  domain_id        = stalwart_domain.manafishrov.id
  member_tenant_id = null
  name             = "postmaster"
  recipients       = ["support@manafishrov.com"]
}

# __generated__ by OpenTofu from "jdzlxtbqarqa"
resource "stalwart_tracer_stdout" "stdout" {
  ansi          = false
  buffered      = false
  enable        = true
  events        = null
  events_policy = "exclude"
  level         = "info"
  lossy         = false
  multiline     = false
}

# __generated__ by OpenTofu from "jdzlxtboapaa"
resource "stalwart_mta_route_relay" "mx" {
  address             = "smtp.resend.com"
  allow_invalid_certs = false
  # The API returns write-only values masked. Keeping the imported Value
  # source with a null secret makes the provider preserve the existing value.
  auth_secret = {
    file_path     = null
    secret        = null
    type          = "Value"
    variable_name = null
  }
  auth_username = "resend"
  description   = "Resend smarthost for external Manafish mail"
  implicit_tls  = true
  name          = "mx"
  port          = 465
  protocol      = "smtp"
}

# __generated__ by OpenTofu from "jdzlxs2saiaa"
resource "stalwart_certificate" "wildcard" {
  certificate = {
    file_path     = "/var/lib/stalwart/private/tls/tls.crt"
    type          = "File"
    value         = null
    variable_name = null
  }
  private_key = {
    file_path     = "/var/lib/stalwart/private/tls/tls.key"
    secret        = null # sensitive
    type          = "File"
    variable_name = null
  }
}

# __generated__ by OpenTofu from "jdzlxs2uamqa"
resource "stalwart_dkim_signature_dkim1_ed25519_sha256" "manafishrov" {
  auid               = null
  canonicalization   = "relaxed/relaxed"
  domain_id          = stalwart_domain.manafishrov.id
  expire             = null
  headers            = ["Date", "From", "Message-ID", "Subject", "To"]
  member_tenant_id   = null
  next_transition_at = null
  private_key = {
    file_path     = "/var/lib/stalwart/private/dkim/manafishrov.com.ed25519.key"
    secret        = null # sensitive
    type          = "File"
    variable_name = null
  }
  report           = true
  selector         = "stalwart-ed25519"
  stage            = "active"
  third_party      = null
  third_party_hash = null
}

# __generated__ by OpenTofu from "singleton"
resource "stalwart_imap" "this" {
  allow_plain_text_auth    = false
  max_auth_failures        = 30
  max_concurrent           = 16
  max_messages_per_command = 1000000
  max_messages_per_save    = 1000000
  max_request_rate = {
    count  = 2000
    period = 60000
  }
  max_request_size      = 52428800
  max_uid_batches       = 10000
  min_uid_batch_size    = 500
  timeout_anonymous     = 60000
  timeout_authenticated = 1800000
  timeout_idle          = 1800000
}

# __generated__ by OpenTofu from "jdzlxs2qadaa"
resource "stalwart_network_listener" "submission" {
  bind                            = ["[::]:587"]
  max_connections                 = 8192
  name                            = "submission"
  override_proxy_trusted_networks = null
  protocol                        = "smtp"
  socket_backlog                  = 1024
  socket_no_delay                 = true
  socket_receive_buffer_size      = null
  socket_reuse_address            = true
  socket_reuse_port               = true
  socket_send_buffer_size         = null
  socket_tos_v4                   = null
  socket_ttl                      = null
  tls_disable_cipher_suites       = null
  tls_disable_protocols           = null
  tls_ignore_client_order         = true
  tls_implicit                    = false
  tls_timeout                     = 60000
  use_tls                         = true
}

# __generated__ by OpenTofu from "jdzlxs2qacaa"
resource "stalwart_network_listener" "submissions" {
  bind                            = ["[::]:465"]
  max_connections                 = 8192
  name                            = "submissions"
  override_proxy_trusted_networks = null
  protocol                        = "smtp"
  socket_backlog                  = 1024
  socket_no_delay                 = true
  socket_receive_buffer_size      = null
  socket_reuse_address            = true
  socket_reuse_port               = true
  socket_send_buffer_size         = null
  socket_tos_v4                   = null
  socket_ttl                      = null
  tls_disable_cipher_suites       = null
  tls_disable_protocols           = null
  tls_ignore_client_order         = true
  tls_implicit                    = true
  tls_timeout                     = 60000
  use_tls                         = true
}

# __generated__ by OpenTofu from "singleton"
resource "stalwart_sender_auth" "this" {
  arc_verify = {
    else  = "disable"
    match = null
  }
  dkim_sign_domain = {
    else = "false"
    match = [
      {
        if   = "is_local_domain(sender_domain) && !is_empty(authenticated_as)"
        then = "sender_domain"
      },
    ]
  }
  dkim_strict = true
  dkim_verify = {
    else = "relaxed"
    match = [
      {
        if   = "listener == 'edge-lmtp'"
        then = "disable"
      },
    ]
  }
  dmarc_verify = {
    else = "disable"
    match = [
      {
        if   = "local_port == 25"
        then = "relaxed"
      },
    ]
  }
  reverse_ip_verify = {
    else = "disable"
    match = [
      {
        if   = "local_port == 25"
        then = "relaxed"
      },
    ]
  }
  spf_ehlo_verify = {
    else = "disable"
    match = [
      {
        if   = "local_port == 25"
        then = "relaxed"
      },
    ]
  }
  spf_from_verify = {
    else = "disable"
    match = [
      {
        if   = "local_port == 25"
        then = "relaxed"
      },
    ]
  }
}

# __generated__ by OpenTofu from "c"
resource "stalwart_domain" "manafishrov" {
  aliases           = null
  allow_relaying    = false
  catch_all_address = null
  certificate_management = {
    acme_provider_id          = null
    subject_alternative_names = null
    type                      = "Manual"
  }
  description  = null
  directory_id = null
  dkim_management = {
    algorithms        = null
    delete_after      = null
    retire_after      = null
    rotate_after      = null
    selector_template = null
    type              = "Manual"
  }
  dns_management = {
    dns_server_id   = null
    origin          = null
    publish_records = null
    type            = "Manual"
  }
  is_enabled         = true
  logo               = null
  member_tenant_id   = null
  name               = "manafishrov.com"
  report_address_uri = "mailto:postmaster@manafishrov.com"
  sub_addressing = {
    custom_rule = null
    type        = "Enabled"
  }
}

# __generated__ by OpenTofu from "jdzlxs2qaeaa"
resource "stalwart_network_listener" "imaps" {
  bind                            = ["[::]:993"]
  max_connections                 = 8192
  name                            = "imaps"
  override_proxy_trusted_networks = null
  protocol                        = "imap"
  socket_backlog                  = 1024
  socket_no_delay                 = true
  socket_receive_buffer_size      = null
  socket_reuse_address            = true
  socket_reuse_port               = true
  socket_send_buffer_size         = null
  socket_tos_v4                   = null
  socket_ttl                      = null
  tls_disable_cipher_suites       = null
  tls_disable_protocols           = null
  tls_ignore_client_order         = true
  tls_implicit                    = true
  tls_timeout                     = 60000
  use_tls                         = true
}

# __generated__ by OpenTofu from "jdzlxs2qabaa"
resource "stalwart_network_listener" "edge_lmtp" {
  bind                            = ["[::]:24"]
  max_connections                 = 8192
  name                            = "edge-lmtp"
  override_proxy_trusted_networks = null
  protocol                        = "lmtp"
  socket_backlog                  = 1024
  socket_no_delay                 = true
  socket_receive_buffer_size      = null
  socket_reuse_address            = true
  socket_reuse_port               = true
  socket_send_buffer_size         = null
  socket_tos_v4                   = null
  socket_ttl                      = null
  tls_disable_cipher_suites       = null
  tls_disable_protocols           = null
  tls_ignore_client_order         = true
  tls_implicit                    = true
  tls_timeout                     = 60000
  use_tls                         = true
}

# __generated__ by OpenTofu from "b"
resource "stalwart_domain" "system" {
  aliases           = null
  allow_relaying    = false
  catch_all_address = null
  certificate_management = {
    acme_provider_id          = null
    subject_alternative_names = null
    type                      = "Manual"
  }
  description  = null
  directory_id = null
  dkim_management = {
    algorithms        = null
    delete_after      = null
    retire_after      = null
    rotate_after      = null
    selector_template = null
    type              = "Manual"
  }
  dns_management = {
    dns_server_id   = null
    origin          = null
    publish_records = null
    type            = "Manual"
  }
  is_enabled         = true
  logo               = null
  member_tenant_id   = null
  name               = "system.manafishrov.com"
  report_address_uri = "mailto:postmaster"
  sub_addressing = {
    custom_rule = null
    type        = "Enabled"
  }
}

# __generated__ by OpenTofu from "jdzlxlo7aaab"
resource "stalwart_application" "webui" {
  auto_update_frequency = 2592000000
  description           = "Stalwart Web Interface"
  enabled               = true
  resource_url          = "file:///nix/store/7x2xs13brrsjiys55kzf1gj8vw4w15ag-stalwart-webui-no-upsell-1.0.10"
  unpack_directory      = null
  url_prefix            = ["/account", "/admin"]
}

# __generated__ by OpenTofu from "jdzlxs2ualqa"
resource "stalwart_dkim_signature_dkim1_rsa_sha256" "manafishrov" {
  auid               = null
  canonicalization   = "relaxed/relaxed"
  domain_id          = stalwart_domain.manafishrov.id
  expire             = null
  headers            = ["Date", "From", "Message-ID", "Subject", "To"]
  member_tenant_id   = null
  next_transition_at = null
  private_key = {
    file_path     = "/var/lib/stalwart/private/dkim/manafishrov.com.rsa.key"
    secret        = null # sensitive
    type          = "File"
    variable_name = null
  }
  report           = true
  selector         = "stalwart-rsa"
  stage            = "active"
  third_party      = null
  third_party_hash = null
}

# __generated__ by OpenTofu from "jdzlxs2qafaa"
resource "stalwart_network_listener" "sieve" {
  bind                            = ["[::]:4190"]
  max_connections                 = 8192
  name                            = "sieve"
  override_proxy_trusted_networks = null
  protocol                        = "manageSieve"
  socket_backlog                  = 1024
  socket_no_delay                 = true
  socket_receive_buffer_size      = null
  socket_reuse_address            = true
  socket_reuse_port               = true
  socket_send_buffer_size         = null
  socket_tos_v4                   = null
  socket_ttl                      = null
  tls_disable_cipher_suites       = null
  tls_disable_protocols           = null
  tls_ignore_client_order         = true
  tls_implicit                    = false
  tls_timeout                     = 60000
  use_tls                         = true
}

# __generated__ by OpenTofu from "singleton"
resource "stalwart_system_settings" "this" {
  default_certificate_id = stalwart_certificate.wildcard.id
  default_domain_id      = stalwart_domain.manafishrov.id
  default_hostname       = "mail.manafishrov.com"
  mail_exchangers = [
    {
      hostname = null
      priority = 10
    },
  ]
  max_connections        = 8192
  provider_info          = {}
  proxy_trusted_networks = null
  thread_pool_size       = null
}

# __generated__ by OpenTofu from "jdzlxs2qagaa"
resource "stalwart_network_listener" "http" {
  bind                            = ["[::]:8080"]
  max_connections                 = 8192
  name                            = "http"
  override_proxy_trusted_networks = null
  protocol                        = "http"
  socket_backlog                  = 1024
  socket_no_delay                 = true
  socket_receive_buffer_size      = null
  socket_reuse_address            = true
  socket_reuse_port               = true
  socket_send_buffer_size         = null
  socket_tos_v4                   = null
  socket_ttl                      = null
  tls_disable_cipher_suites       = null
  tls_disable_protocols           = null
  tls_ignore_client_order         = true
  tls_implicit                    = false
  tls_timeout                     = 60000
  use_tls                         = false
}

# __generated__ by OpenTofu from "jdzlxs2qahaa"
resource "stalwart_network_listener" "https" {
  bind                            = ["[::]:443"]
  max_connections                 = 8192
  name                            = "https"
  override_proxy_trusted_networks = null
  protocol                        = "http"
  socket_backlog                  = 1024
  socket_no_delay                 = true
  socket_receive_buffer_size      = null
  socket_reuse_address            = true
  socket_reuse_port               = true
  socket_send_buffer_size         = null
  socket_tos_v4                   = null
  socket_ttl                      = null
  tls_disable_cipher_suites       = null
  tls_disable_protocols           = null
  tls_ignore_client_order         = true
  tls_implicit                    = true
  tls_timeout                     = 60000
  use_tls                         = true
}

# __generated__ by OpenTofu from "singleton"
resource "stalwart_mta_stage_data" "this" {
  add_auth_results_header = {
    else = "false"
    match = [
      {
        if   = "local_port == 25"
        then = "true"
      },
    ]
  }
  add_date_header = {
    else = "false"
    match = [
      {
        if   = "local_port == 25"
        then = "true"
      },
    ]
  }
  add_delivered_to_header = true
  add_message_id_header = {
    else = "false"
    match = [
      {
        if   = "local_port == 25"
        then = "true"
      },
    ]
  }
  add_received_header = {
    else = "false"
    match = [
      {
        if   = "local_port == 25"
        then = "true"
      },
    ]
  }
  add_received_spf_header = {
    else = "false"
    match = [
      {
        if   = "local_port == 25"
        then = "true"
      },
    ]
  }
  add_return_path_header = {
    else = "false"
    match = [
      {
        if   = "local_port == 25"
        then = "true"
      },
    ]
  }
  enable_spam_filter = {
    else = "is_empty(authenticated_as)"
    match = [
      {
        if   = "listener == 'edge-lmtp'"
        then = "false"
      },
    ]
  }
  max_message_size = {
    else  = "104857600"
    match = null
  }
  max_messages = {
    else  = "10"
    match = null
  }
  max_received_headers = {
    else  = "50"
    match = null
  }
  script = {
    else  = "false"
    match = null
  }
}
