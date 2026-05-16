data "cloudflare_zone" "manafishrov" {
  filter = {
    name = "manafishrov.com"
  }
}

locals {
  dns_records = {

    website = {
      name    = "www"
      type    = "A"
      content = "185.158.133.1"
    }
    lovable_website = {
      name    = "_lovable.www"
      type    = "TXT"
      content = "lovable_verify=9d45e49616e85ed56fb7a8f0b4b37e3fe60b1b69f88acad682aeb158a6ef3bc6"
    }

    files = {
      name    = "files"
      type    = "A"
      content = "185.158.133.1"
    }
    lovable_files = {
      name    = "_lovable.files"
      type    = "TXT"
      content = "lovable_verify=1633dd859817ff1068321b7dd3f0fa29bdb51a5cd7a4e94962465cd91130c1dc"
    }

    sim = {
      name    = "sim"
      type    = "A"
      content = "185.158.133.1"
    }
    lovable_sim = {
      name    = "_lovable.sim"
      type    = "TXT"
      content = "lovable_verify=868dafebfa40ff43475f6a3a4c9c535837b9a2f7ecd4dc245bf2a50034863bf0"
    }

    beta = {
      name    = "beta"
      type    = "CNAME"
      content = "cname.super.so"
    }

    landing = {
      name    = "landing"
      type    = "CNAME"
      content = "manafishrov.github.io"
    }
    ui = {
      name    = "ui"
      type    = "CNAME"
      content = "manafishrov.github.io"
    }

    s3 = {
      name    = "s3"
      type    = "CNAME"
      content = "router.gullhaugveien.michaelbrusegard.com"
    }
    id = {
      name    = "id"
      type    = "CNAME"
      content = "router.gullhaugveien.michaelbrusegard.com"
    }
    vault = {
      name    = "vault"
      type    = "CNAME"
      content = "router.gullhaugveien.michaelbrusegard.com"
    }

    dmarc = {
      name    = "_dmarc"
      type    = "TXT"
      content = "v=DMARC1; p=quarantine;"
    }

    dkim_k2_updates = {
      name    = "k2._domainkey.updates"
      type    = "CNAME"
      content = "dkim2.mcsv.net"
    }
    dkim_k3_updates = {
      name    = "k3._domainkey.updates"
      type    = "CNAME"
      content = "dkim3.mcsv.net"
    }

    protonmail_domainkey_updates = {
      name    = "protonmail._domainkey.updates"
      type    = "CNAME"
      content = "protonmail.domainkey.dvobtm6qh2g4ugep6qy5niizj5ksma5s7hdehpq7igj63htmwngja.domains.proton.ch"
    }
    protonmail2_domainkey_updates = {
      name    = "protonmail2._domainkey.updates"
      type    = "CNAME"
      content = "protonmail2.domainkey.dvobtm6qh2g4ugep6qy5niizj5ksma5s7hdehpq7igj63htmwngja.domains.proton.ch"
    }
    protonmail3_domainkey_updates = {
      name    = "protonmail3._domainkey.updates"
      type    = "CNAME"
      content = "protonmail3.domainkey.dvobtm6qh2g4ugep6qy5niizj5ksma5s7hdehpq7igj63htmwngja.domains.proton.ch"
    }

    updates_mx_protonmail = {
      name     = "updates"
      type     = "MX"
      content  = "mail.protonmail.ch"
      priority = 20
    }
    updates_mx_protonmail_sec = {
      name     = "updates"
      type     = "MX"
      content  = "mailsec.protonmail.ch"
      priority = 30
    }
    updates_spf = {
      name    = "updates"
      type    = "TXT"
      content = "v=spf1 include:_spf.protonmail.ch ~all"
    }
    updates_protonmail_verification = {
      name    = "updates"
      type    = "TXT"
      content = "protonmail-verification=acc7d667357e78d99f1a07a06b39bf6ffe63b11f"
    }

    send_updates_mx = {
      name     = "send.updates"
      type     = "MX"
      content  = "feedback-smtp.eu-west-1.amazonses.com"
      priority = 10
    }
    send_updates_spf = {
      name    = "send.updates"
      type    = "TXT"
      content = "v=spf1 include:amazonses.com -all"
    }

    resend_domainkey_updates = {
      name    = "resend._domainkey.updates"
      type    = "TXT"
      content = "p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDL3dpUyho6F57ks3Gkl6l5v8goijjgshbz3WRr3KLapemuhKoGoHothE3YKyHlw7hSIreChyoWHr4QACFNNHZivJD1vfhb+f3UBMp+4TSfZkGVs1IM3jKTMZWo28gUk4qOXVyztN4TktgAP7Yw+RT/elZAT2cL5WMk1mvvB5QBUQIDAQAB"
    }
  }
}

resource "cloudflare_dns_record" "manafishrov" {
  for_each = local.dns_records

  zone_id  = data.cloudflare_zone.manafishrov.id
  name     = each.value.name
  type     = each.value.type
  content  = each.value.content
  ttl      = try(each.value.ttl, 1)
  proxied  = try(each.value.proxied, false)
  priority = try(each.value.priority, null)
}
