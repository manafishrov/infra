# Stalwart and Bulwark preview

Stalwart administration is at `https://mail-admin.manafishrov.com`.
Bulwark 1.9.2 is staged at `https://mail-preview.manafishrov.com` in the same
namespace, pinned by image digest. `mail.manafishrov.com` still serves Roundcube;
SMTP, IMAP and MX routing are unchanged.

The preview uses the migrated mailbox snapshot, not ongoing delivery. Do not
use it as the primary mailbox or send production mail before cutover. Changes
to messages in the preview affect the destination mailstore and must be
accounted for during the final migration delta.

## Authentication and configuration

Bulwark uses Pocket ID with the existing public `stalwart` PKCE client because
Stalwart validates that client audience. The preview callback is declared in
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

Stalwart's pre-authentication HTTP budget is 2,000 requests/minute because external
OIDC requests bypass the native credential cache and share a gateway address.
The authenticated account budget remains 1,000/minute; failed-login protections
remain unchanged. Forwarded headers are not trusted indiscriminately.

## Acceptance before cutover

- Sign in through Pocket ID and confirm the personal mailbox opens.
- Confirm shared mailboxes match Pocket ID memberships and can be opened.
- Check folder lists and representative migrated messages without moving or
  deleting production messages. Do not treat old snapshot counts as new mail.
- Test a non-administrator's login and shared-mailbox isolation.
- Confirm sign-out and a fresh login work.

A successful redirect alone does not prove authenticated JMAP access. Real
passkey login and shared-mailbox checks require the corresponding user.

Production cutover needs a final mailbox delta, SMTP/IMAP authentication tests,
explicit routing authorization, and verification of the Manata backup/restore
path when the backup host becomes available. Keep Roundcube and source mail
until rollback is no longer needed.
