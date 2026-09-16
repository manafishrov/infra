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
