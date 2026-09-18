# Junk-only handling: Postfix already accepted the message into its queue.
# Native authentication and contact/reply learning run here, not at the edge.
resource "stalwart_spam_settings" "this" {
  enable                = true
  score_spam            = 5
  score_reject          = 0
  score_discard         = 0
  trust_contacts        = true
  trust_replies         = true
  spam_filter_rules_url = "https://github.com/stalwartlabs/spam-filter/releases/download/v3.0.1/spam-filter-rules.json.gz"
}

resource "stalwart_spam_pyzor" "this" {
  enable = false
}

resource "stalwart_spam_llm" "this" {
  type = "Disable"
}

# Convert the existing Reject variant in place BEFORE importing this resource.
# Preserve its ID and all other Score weights. Do not create a duplicate tag.
resource "stalwart_spam_tag_score" "blocked_domain" {
  count = var.smtp_edge_activation_ready ? 1 : 0

  lifecycle {
    prevent_destroy = true
  }

  tag   = "BLOCKED_DOMAIN"
  score = 1000
}

import {
  to = stalwart_spam_settings.this
  id = "singleton"
}
import {
  to = stalwart_spam_pyzor.this
  id = "singleton"
}
import {
  to = stalwart_spam_llm.this
  id = "singleton"
}
import {
  for_each = var.smtp_edge_activation_ready ? toset(["jdzlxyqedpaa"]) : toset([])
  to       = stalwart_spam_tag_score.blocked_domain[0]
  id       = each.value
}
