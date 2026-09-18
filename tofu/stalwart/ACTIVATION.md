# Private SMTP activation gates

Only the production tf-controller may plan/apply this stack. Local checks use
an isolated copy, `init -backend=false`, and `validate`, without credentials.
This document describes future operator actions, not actions already taken.

`smtp_edge_activation_ready` defaults to false. Preparation therefore leaves
both new listeners absent, DATA filtering off, and the BLOCKED_DOMAIN Score
resource/import absent. The existing `edge-lmtp` listener on port 24 remains
unchanged for recipient verification, queue drain, and rollback.

## Ordering

1. Review the production controller's preparation plan with the activation
   flag false. Preserve DKIM custody/Manual rotation, domains, SCIM, storage,
   Resend, OIDC, and submission settings. Reconcile only after approval.
   Confirm spam threshold 5, reject/discard thresholds 0, Pyzor disabled, LLM
   disabled, contacts/replies trusted, and no old authentication-score bridge
   overrides. Keep the stock weights other than BLOCKED_DOMAIN.
2. Verify runtime filtering is off for the old edge and the new paths. API
   values alone are not proof of the running configuration. Under an approved
   maintenance procedure, convert the existing SpamTag ID `jdzlxyqedpaa` from
   Reject to Score 1000 in place (`convert-blocked-domain.json` is the request
   template after that readback). Do not create a second BLOCKED_DOMAIN tag or
   import the Reject variant as `stalwart_spam_tag_score`.
3. Reload/restart Stalwart as required by the qualified native procedure;
   verify the persisted variant and the running safety settings. This step
   must finish before the Score import or SMTP/25 filtering is enabled.
   Recheck the shared-edge abuse-ban setting is null; `security.tf` detects
   drift but provider 0.2.3 cannot clear that Optional+Computed field itself.
4. Install and verify the exact `smtp-edge` namespace AND app Cilium identity
   restriction before exposing ports 25/26. Set `smtp_edge_proxy_networks` to
   the consumer pod networks (currently `10.42.0.0/16` and `fd42::/56`). These
   CIDRs select PROXY parsing; they do not authorize callers. Native Stalwart
   rejects prefixes shorter than /8. Do not enable global PROXY trust.
5. Before changing domain sub-addressing, account for already accepted mail.
   Read complete, metadata-only old-edge and backend queue inventories (all
   pages and totals, no message bodies). Any queued implicit-plus recipient
   must drain while sub-addressing is still Enabled, or have its destination
   explicitly preserved and verified. If that accounting cannot exclude an
   ingress race, quiesce old SMTP acceptance, let existing sessions finish and
   drain before proceeding. An empty first page is not proof of an empty queue.
   Do not defer this check until after activation; a later global plus-resolution
   change can otherwise permanently reject previously accepted mail.
   Then set `smtp_edge_activation_ready = true` in the production controller vars.
   Review its plan: import Score ID `jdzlxyqedpaa` at
   `stalwart_spam_tag_score.blocked_domain[0]`, enable filtering only on
   `smtp-edge`, and create SMTP/25 and SMTP/26 after the safety settings.
   Activation also disables native sub-addressing for `manafishrov.com`.
   This changes backend plus-address resolution globally for that domain,
   including LMTP verification and every delivery path, not just SMTP/25.
   It restores the public edge's existing exact-address contract: explicitly
   configured plus aliases remain valid, but undefined plus addresses must
   not resolve to a base mailbox. Postfix's empty `recipient_delimiter` alone
   cannot enforce this while native sub-addressing is enabled. Preparation
   retains Enabled; internal/test domains keep their current settings.
   No unrelated resource replacement or DKIM key rotation is expected.
6. After the approved controller reconciliation and any required listener
   restart, verify STARTTLS (not implicit TLS) on both new listeners; PROXY
   only on SMTP/25; restored original IP/EHLO on SMTP/25; no SASL or external
   relay on all three private paths; and no sender-auth/filter/signing on
   SMTP/26. Confirm native classification and BLOCKED_DOMAIN Junk delivery
   without reject/discard. Contact/reply trust may override even Score 1000.
   Keep forged message headers unchanged; do not add a score bridge.
   Require the full-Postfix fixture to prove that an explicitly configured
   plus alias is accepted and an undefined plus address is rejected by native
   recipient verification. Do not substitute a runtime script or workaround.
7. Only then switch public mail to Postfix. Keep the old edge/LMTP path until
   queues drain and rollback is no longer required. Qualification scripts and
   Kubernetes cutover are owned outside this stack.

## Rollback

Keep the activation flag true after import. The Score resource has
`prevent_destroy`; changing the flag back to false is deliberately not a
rollback mechanism. Route traffic back through the retained old edge/LMTP
path under the separately approved cutover procedure. Do not restore the
Reject action, delete the existing Score tag, or turn on LMTP filtering.
