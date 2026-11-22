# Adopt the DKIM selector records Stalwart published, so OpenTofu takes them
# over in place instead of creating duplicates.
import {
  to = cloudflare_dns_record.manafishrov["stalwart_dkim_rsa"]
  id = "0103f2d05cbe60fbfae44c4b4cb8a191/ac4781451f1dcdd8889e461383646aeb"
}
import {
  to = cloudflare_dns_record.manafishrov["stalwart_dkim_ed25519"]
  id = "0103f2d05cbe60fbfae44c4b4cb8a191/b2e15357fb08d5948457abf5cbc3654a"
}
