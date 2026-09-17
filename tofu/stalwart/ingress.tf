# Direct Internet delivery. SMTP submission remains authenticated; this
# listener accepts only native local recipients, not arbitrary relaying.
resource "stalwart_network_listener" "smtp" {
  name         = "smtp"
  protocol     = "smtp"
  bind         = ["[::]:25"]
  use_tls      = true
  tls_implicit = false
}
