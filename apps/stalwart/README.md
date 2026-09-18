# Manafishrov mail backend

Stalwart owns mailboxes, native SCIM/OIDC, authenticated submission, DKIM,
spam classification and learning. Bulwark is the mail UI. Public incoming mail
arrives through the personal infrastructure's routing-only Postfix edge.

Private listeners require the exact `smtp-edge` namespace and app identity:

- TLS LMTP/24: native recipient verification, stopping at RCPT.
- STARTTLS SMTP/25: queued mail with protected original IP/EHLO via PROXY;
  native relaxed sender authentication and Junk-only spam filtering.
- STARTTLS SMTP/26: Postfix-generated mail, without PROXY/authentication checks
  or spam filtering. None of these paths allows unauthenticated external relay.

Postfix has no backend management credential. Incoming Authentication-Results
headers remain intact for signature verification but are not the trust source.
BLOCKED_DOMAIN is Score 1000; reject/discard thresholds are zero. Contact/reply
trust and stock authentication behavior remain enabled. Undefined plus addresses
are disabled for `manafishrov.com`; explicit plus aliases still resolve.

`tofu/stalwart/ACTIVATION.md` describes the separate listener and recipient-policy
gates. Production plans/applies run only through the reviewed tf-controller.
The old Stalwart edge's network access is removed after quiesced queue drain.
Mailbox storage, native identity, DKIM keys/selectors and unrelated services are
unchanged by the Postfix replacement.
