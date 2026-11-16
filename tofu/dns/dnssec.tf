# Cloudflare registers manafishrov.com, so enabling DNSSEC here also
# publishes the DS record at .com; no registrar step is needed.
resource "cloudflare_zone_dnssec" "manafishrov" {
  zone_id = data.cloudflare_zone.manafishrov.zone_id
  status  = "active"
}
