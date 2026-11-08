# __generated__ by OpenTofu from "singleton"
resource "stalwart_mta_sts" "this" {
  max_age = 604800000
  mode    = "testing"
  # Publish both names while cached policies and the branded MX converge.
  mx_hosts = ["mx.manafishrov.com"]
}

# __generated__ by OpenTofu from "singleton"
resource "stalwart_authentication" "this" {
  default_admin_role_ids  = ["b", "e"]
  default_group_role_ids  = ["c"]
  default_user_role_ids   = ["b"]
  directory_id            = stalwart_directory_oidc.pocket_id.id
  max_api_keys            = 5
  max_app_passwords       = 5
  password_default_expiry = null
  password_hash_algorithm = "argon2id"
  max_password_length     = 128
  min_password_length     = 8
  min_password_strength   = "three"
}

# __generated__ by OpenTofu from "jdzlxs2sajaa"
resource "stalwart_directory_oidc" "pocket_id" {
  claim_groups             = "groups"
  claim_name               = "name"
  claim_username           = "email"
  description              = "Pocket ID for manafishrov.com"
  issuer_url               = "https://id.manafishrov.com"
  member_tenant_id         = null
  accepted_audiences       = ["stalwart"]
  skip_audience_validation = false
  opaque_token_validation  = "userInfo"
  # Preserve Pocket ID administration as well as webmail. These tokens have
  # openid/email scopes, not Stalwart scopes; account roles still bound access.
  unscoped_tokens       = "full"
  allow_id_token_claims = false
  lenient_issuer_match  = false
  allow_invalid_certs   = false
  username_domain       = "manafishrov.com"
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
  host                = "smtp.resend.com"
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

# __generated__ by OpenTofu from "singleton"
resource "stalwart_imap" "this" {
  allow_plain_text_auth      = false
  max_auth_failures          = 30
  max_concurrent_connections = 16
  max_messages_per_command   = 1000000
  max_messages_per_save      = 1000000
  rate_limit = {
    count  = 2000
    period = 60000
  }
  max_request_size      = 52428800
  max_uid_batches       = 10000
  min_uid_batch_size    = 500
  anonymous_timeout     = 60000
  authenticated_timeout = 1800000
  idle_timeout          = 1800000
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
  implicit_tls                    = false
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
  implicit_tls                    = true
  tls_timeout                     = 60000
  use_tls                         = true
}

# __generated__ by OpenTofu from "singleton"
resource "stalwart_sender_auth" "this" {
  arc_verify = {
    else  = "disable"
    match = null
  }
  dkim_strict = true
  dkim_verify = {
    else = "relaxed"
    match = [
      {
        if   = "listener == 'edge-lmtp' || listener == 'smtp-edge-local'"
        then = "disable"
      },
    ]
  }
  dmarc_verify = {
    else = "disable"
    match = [
      {
        if   = "listener == 'smtp-edge'"
        then = "relaxed"
      },
    ]
  }
  reverse_ip_verify = {
    else = "disable"
    match = [
      {
        if   = "listener == 'smtp-edge'"
        then = "relaxed"
      },
    ]
  }
  spf_ehlo_verify = {
    else = "disable"
    match = [
      {
        if   = "listener == 'smtp-edge'"
        then = "relaxed"
      },
    ]
  }
  spf_from_verify = {
    else = "disable"
    match = [
      {
        if   = "listener == 'smtp-edge'"
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
    dns_server_id   = stalwart_dns_server_cloudflare.dkim.id
    origin          = "manafishrov.com"
    publish_records = ["dkim"]
    type            = "Automatic"
  }
  enable             = true
  logo               = null
  member_tenant_id   = null
  name               = "manafishrov.com"
  report_address_uri = "mailto:postmaster@manafishrov.com"
  sub_addressing = {
    custom_rule = null
    type        = var.smtp_edge_exact_recipients_ready ? "Disabled" : "Enabled"
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
  implicit_tls                    = true
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
  implicit_tls                    = true
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
  enable             = true
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
  auto_update_interval = 2592000000
  description          = "Stalwart Web Interface"
  enable               = true
  # Pocket ID releases the groups claim only for this scope; OIDC admin
  # rights depend on it. Migrated records do not get the fork's default.
  oauth_scopes     = ["groups"]
  resource_url     = "file:///nix/store/qs0lm3w840jrb48z2a488zpfw0yfz6fr-stalwart-webui-no-upsell-2.0.5"
  unpack_directory = null
  url_prefix       = ["/account", "/admin"]
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
  implicit_tls                    = false
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
  lifecycle {
    postcondition {
      condition     = self.proxy_trusted_networks == null ? true : length(self.proxy_trusted_networks) == 0
      error_message = "Global PROXY trust is forbidden; scope it to the private smtp-edge listener."
    }
  }
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
  implicit_tls                    = false
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
  implicit_tls                    = true
  tls_timeout                     = 60000
  use_tls                         = true
}

# __generated__ by OpenTofu from "singleton"
resource "stalwart_mta_stage_data" "this" {
  dkim_sign_domain = {
    else = "false"
    match = [
      {
        if   = "is_local_domain(sender_domain) && !is_empty(authenticated_as)"
        then = "sender_domain"
      },
    ]
  }

  depends_on = [
    stalwart_spam_settings.this,
    stalwart_spam_tag_score.blocked_domain,
    stalwart_spam_pyzor.this,
  ]
  add_auth_results_header = {
    else = "false"
    match = [
      {
        if   = "listener == 'smtp-edge'"
        then = "true"
      },
    ]
  }
  add_date_header = {
    else = "false"
    match = [
      {
        if   = "listener == 'smtp-edge'"
        then = "true"
      },
    ]
  }
  add_delivered_to_header = true
  add_message_id_header = {
    else = "false"
    match = [
      {
        if   = "listener == 'smtp-edge'"
        then = "true"
      },
    ]
  }
  add_received_header = {
    else = "false"
    match = [
      {
        if   = "listener == 'smtp-edge'"
        then = "true"
      },
    ]
  }
  add_received_spf_header = {
    else = "false"
    match = [
      {
        if   = "listener == 'smtp-edge'"
        then = "true"
      },
    ]
  }
  add_return_path_header = {
    else = "false"
    match = [
      {
        if   = "listener == 'smtp-edge'"
        then = "true"
      },
    ]
  }
  enable_spam_filter = {
    else = "false"
    match = [
      {
        if   = "listener == 'smtp-edge'"
        then = var.smtp_edge_activation_ready ? "true" : "false"
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
