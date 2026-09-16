# Bulwark connects directly to JMAP from the browser after Pocket ID login.
# Restrict cross-origin access to the preview rather than enabling wildcard CORS.
resource "stalwart_http" "server" {
  use_permissive_cors = false
  enable_hsts         = false
  use_x_forwarded     = false
  redirect_root       = "/account"
  allowed_endpoints = {
    else  = "200"
    match = []
  }
  rate_limit_authenticated = {
    count  = 1000
    period = 60000
  }
  # Known OIDC tokens use admission-only hints, not cached authorization.
  # Every request still revalidates claims/account state and uses the account
  # budget (including privileged OIDC sessions). Unknown tokens remain subject
  # to this original IP-based budget; forwarding headers remain untrusted.
  rate_limit_anonymous = {
    count  = 100
    period = 60000
  }
  response_headers = {
    "Access-Control-Allow-Origin"  = "https://mail-preview.manafishrov.com"
    "Access-Control-Allow-Methods" = "GET, HEAD, POST, OPTIONS"
    "Access-Control-Allow-Headers" = "Authorization, Content-Type, Accept, Last-Event-ID"
  }
}
