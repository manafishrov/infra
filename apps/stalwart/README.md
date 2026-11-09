# Manafishrov mail backend

Stalwart owns mailboxes, native SCIM/OIDC, authenticated submission, DKIM,
spam classification and learning. Public incoming mail arrives through the
personal infrastructure's routing-only Postfix edge.

Bulwark 1.21.0 serves `https://webmail.manafishrov.com`, pinned by image digest.
Stalwart JMAP and administration use `https://mail.manafishrov.com`.
The Deployment and Secret are named `bulwark`; the existing settings PVC
and session-key material are preserved. Retired hostnames have no aliases.

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

## DKIM ownership

Stalwart holds the original keys in native Text custody and publishes only DKIM
DNS records using its dedicated Cloudflare credential. The old key mount/Secret
and Terraform key/record ownership are retired. Key rotation and certificate
management remain Manual. See [DKIM operations](../../docs/dkim-handoff/README.md)
for refresh permissions, exact-content checks and the production receipt.

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
protections remain enabled. HTTP client addresses come from the rightmost
`X-Forwarded-For` entry with `forwarded_hops = 1`: Cilium's Envoy Gateway
appends the real client there (`use_remote_address: true`,
`xff_num_trusted_hops: 0`). Earlier entries supplied by a client do not select
the ban/rate-limit address. A missing header falls back to the TCP peer.
Keep HTTP access restricted to the Gateway and existing trusted internal
workloads. SMTP PROXY trust is independent and remains listener-scoped;
shared LMTP recipient probes still require `abuse_ban_rate = null`.

## User acceptance

Use real Pocket ID login to check personal/shared mailbox access, folder lists,
sending from shared identities, non-administrator isolation and fresh login after
sign-out. A redirect alone does not prove authenticated JMAP access; these checks
require the corresponding user.

Android native-app login remains unqualified: mobile 0.1.62's webmail handoff
rejects the separate Pocket ID token-endpoint hostname. Browser success does not
prove mobile compatibility. JMAP-first cutover does not add IMAP client access.

## OpenTofu management

`tofu/stalwart` adopts and manages the production server configuration through
Stalwart's JMAP management API. SCIM continues to own mailbox users, shared
mailbox groups, and their memberships; they are deliberately absent from the
OpenTofu state.

The controller authenticates with an API-key-only system principal whose
permissions are restricted to Stalwart's `sys*` management surface. Human
administration is granted only for OIDC sessions carrying the exact Pocket ID
`mail-admin` group; no native Admin role is persisted. Pocket ID uses a separate,
mailbox-only client as its SCIM synchronization boundary so the authorization
group is never provisioned as a shared mailbox. No recovery or
password-bearing administrator is retained. A completely fresh database
therefore requires a one-time recovery bootstrap to create that principal and
API key; remove the temporary recovery credential immediately after OpenTofu
has adopted the server.

The provider is `michaelbrusegard/stalwart` 1.0.3, built in the personal infra
repo and installed into the runner's filesystem mirror from a pinned image. The
committed lock holds its Darwin arm64 and Linux amd64 `h1` checksums; update
both and the runner image pin whenever the provider binary changes.

## Stalwart v1

The patched v1.0.3 server stores mail and configuration in
`/var/lib/stalwart/data-v1/` on the `data-stalwart-0` PVC. OpenTofu uses the
`manafishrov-stalwart-v1` backend suffix. Retained imports adopt existing
objects by ID and prevent duplicate resources when rebuilding state.

HTTP clients are identified by the rightmost `X-Forwarded-For` hop, which the
Gateway sets, so bans and rate limits apply to real client addresses.

Bulwark 1.21 supports v1. Its issuer remains Pocket ID; do not run Bulwark's
OAuth auto-setup, which configures Stalwart as the issuer.
