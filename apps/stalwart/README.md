# Manafishrov mail backend

Stalwart owns mailboxes, native SCIM/OIDC, authenticated submission, DKIM,
spam classification and learning. Public incoming mail arrives through the
personal infrastructure's routing-only Postfix edge.

Bulwark 1.9.2 serves `https://webmail.manafishrov.com`, pinned by image digest.
The preview address redirects there. Stalwart JMAP and administration use
`https://mail.manafishrov.com`. Existing deployment and Secret names keep
the `bulwark-preview` suffix to preserve settings and session-key continuity.

## Incoming mail

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
unchanged by the Postfix replacement. Reversing a delivery route does not copy
mail back; account for new mail and queues before any rollback.

## Authentication and configuration

Bulwark uses Pocket ID with the existing public `stalwart` PKCE client because
Stalwart validates that client audience. Production callbacks are
declared in `tofu/pocket-id/mail.tf`. Webmail does not request the `groups` scope;
server administration belongs at `mail`, not in the webmail login.

The session encryption key lives in the encrypted sibling secrets repository.
Passwords and custom JMAP endpoints are disabled. Settings sync is enabled with
an encrypted per-user settings store on the 1 GiB `bulwark-settings` PVC. Retain
the session encryption key alongside settings backups. Configuration is
environment-managed and admin configuration is read-only; other runtime state
is ephemeral. Zero-surge updates avoid RWO mount conflicts.

The settings PVC has a separate Manata repository and paused VolSync source;
there is no active backup until Manata is online and the repository is initialized.
The Postfix queue recovery proof does **not** qualify this or backend backups.
Do not contact Manata as part of the edge rollout.

Stalwart's pre-authentication HTTP budget is 100 requests/minute. Previously
verified OIDC tokens use cache entries only for rate admission, never to
reconstruct authorization. Every request revalidates issuer claims and native
permissions; failures evict admission. The account budget is checked before IdP
work and charged after authentication, at 1,000 requests/minute, including
privileged OIDC sessions. Unknown tokens use the IP budget. Failed-login
protections and forwarding-header trust are unchanged.

## User acceptance

Use real Pocket ID login to check personal/shared mailbox access, folder lists,
sending from shared identities, non-administrator isolation and fresh login after
sign-out. A redirect alone does not prove authenticated JMAP access; these checks
require the corresponding user.

Android native-app login remains unqualified: mobile 0.1.62's webmail handoff
rejects the separate Pocket ID token-endpoint hostname. Browser success does not
prove mobile compatibility. JMAP-first cutover does not add IMAP client access.
