# API token is supplied via the CLOUDFLARE_API_TOKEN env var, set by the
# tf-controller runner pod from the `cloudflare-api-token` Secret.
provider "cloudflare" {}
