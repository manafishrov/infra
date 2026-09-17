# Stalwart and Bulwark

Bulwark 1.9.2 serves `https://mail.manafishrov.com`, pinned by image digest.
The preview address redirects there. Stalwart administration remains at
`https://mail-admin.manafishrov.com`. Existing deployment and Secret names keep
the `bulwark-preview` suffix to preserve settings and session-key continuity.

The shared SMTP server forwards Manafish recipients over certificate-verified
LMTP to this backend, before its local-domain delivery rule. This also covers
personal submissions and application mail. MX records and public SMTP/IMAP
ports are unchanged; personal mail still uses the original server.

The final mailbox sync was explicitly skipped for the 2026-09-17 cutover.
Messages present only on the old server since the snapshot remain there for
recovery. Do not delete those mailboxes. Roundcube is stopped and its public
route removed; its database and configuration are retained pending user testing.

## Interim ingress dependency

The old server still validates recipient addresses. Its seven Manafish mailbox
addresses and the postmaster alias must match the new backend; the new server's
postmaster list delivers to support. Freeze address additions, renames, deletions,
alias changes and mailing-list changes until recipient validation is decoupled
or both sides are updated together. SCIM owns the destination identities and
shared memberships, but this bridge is not independent ingress provisioning.
Do not enable catch-all or open relaying to work around a mismatch.

## Authentication and configuration

Bulwark uses Pocket ID with the existing public `stalwart` PKCE client because
Stalwart validates that client audience. Production and preview callbacks are declared in
`tofu/pocket-id/mail.tf`. Webmail does not request the `groups` scope; server
administration belongs at `mail-admin`, not in the webmail login.

The session encryption key lives in the encrypted sibling secrets repository.
Passwords and custom JMAP endpoints are disabled. Settings sync is enabled with
an encrypted per-user settings store on the 1 GiB `bulwark-settings` PVC. The
session encryption key must be retained alongside settings backups. Configuration
is environment-managed and the admin configuration is read-only. Runtime state
outside the settings directory remains ephemeral.

The settings PVC has a separate Manata repository and paused VolSync source;
there is no active backup until Manata is online and the repository is initialized.
The deployment uses zero-surge updates to stop the old replica before replacing
it, avoiding RWO mount conflicts.

Stalwart's original pre-authentication HTTP budget is 100 requests/minute.
Previously verified OIDC tokens use cache entries only for rate admission, never
to reconstruct authorization. Each request revalidates issuer claims and native
account permissions; failures evict admission. The account budget is checked
before IdP work and charged after authentication, at 1,000 requests/minute. This
precheck also applies to privileged OIDC sessions. Unknown tokens still use the
IP budget. Failed-login protections and forwarding-header trust are unchanged.

## User acceptance

- Sign in through Pocket ID and confirm the personal mailbox opens.
- Confirm shared mailboxes match Pocket ID memberships and can be opened.
- Send and receive mail through Bulwark, including a shared sender identity.
- Check folder lists and representative migrated messages. Historical mail
  missing because the final sync was skipped is retained on the old server.
- Test a non-administrator's login and shared-mailbox isolation.
- Confirm sign-out and a fresh login work.

A successful redirect alone does not prove authenticated JMAP access. Real
passkey login and shared-mailbox checks require the corresponding user.

Android native-app login remains unqualified: mobile 0.1.62's webmail handoff
rejects the separate Pocket ID token-endpoint hostname. Browser success does not
prove mobile compatibility. JMAP-first cutover does not add IMAP client access.

Before rolling back delivery, account for mail received or sent on this backend
after cutover. Reversing the route alone does not copy that mail back. Restore
the old local-domain rule and Roundcube route only with an explicit data plan.
Complete Roundcube cleanup after user acceptance; keep the original mailstore.
Verify the Manata backup/restore path when that host becomes available.
