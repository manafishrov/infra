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
Passwords, custom JMAP endpoints and settings sync are not enabled. Configuration
is environment-managed and the admin configuration is read-only. Runtime state
is ephemeral; preferences remain browser-local. No additional persistent volume
or backup destination is introduced by the preview.

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
explicit routing authorization, and a persistence/Manata-backup decision for
Bulwark settings if settings sync is enabled. Keep Roundcube and source mail
until rollback is no longer needed.
