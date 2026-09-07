# Manafish Stalwart migration target

This directory is intentionally not referenced by the repository root
`kustomization.yaml` yet. It is a deploy-inert migration target until the
required encrypted Secrets, DNS records, recipient inventory, and cutover
checks have been completed.

Inbound Internet mail terminates at `stalwart-edge`, where sender
authentication and spam filtering use the real remote address. Accepted mail
is delivered to this backend over a network-policy-restricted, TLS-wrapped
LMTP listener on port 24. Port 25 is intentionally absent from the backend
LoadBalancer so it cannot bypass the edge or repeat SPF/DMARC checks against
the edge pod.

Required Secrets in `manafishrov/infra-secrets/apps/stalwart`:

- `stalwart-env` with `STALWART_ADMIN_PASSWORD`,
  `STALWART_RECOVERY_ADMIN`, `STALWART_MAIL_MASTER_PASSWORD`, and
  `STALWART_RESEND_API_KEY`.
- `stalwart-dkim` with the existing `manafishrov.com.rsa.key` and
  `manafishrov.com.ed25519.key` key material used by the shared Stalwart
  instance. Reusing the existing `stalwart-rsa` and `stalwart-ed25519`
  selectors lets both instances sign valid mail during the rollback window
  without changing DNS.
- `freddo-restic-manafishrov-stalwart-pvc` with the VolSync Restic
  repository credentials.

Create a one-time API key for the edge recipient synchronizer with `Replace`
permissions limited to `sysDomainGet`, `sysDomainQuery`, `sysAccountGet`,
`sysAccountQuery`, `sysMailingListGet`, and `sysMailingListQuery`. Store the
generated secret only in the personal infrastructure's `stalwart-edge-env`
Secret as `STALWART_MANAFISH_SYNC_TOKEN`. Network policy permits the edge to
use HTTPS for this read-only inventory and LMTP for delivery; it grants no
other cross-namespace access.

Keep DNS and DKIM management manual during migration. After the new backend
and edge are stable, Stalwart can take ownership of the mail records in a
separate change, with no record managed simultaneously by OpenTofu and
Stalwart.

Before activation:

1. Copy the existing Manafish DKIM keys into the new encrypted Secret without
   removing them from the shared Stalwart instance.
2. Add every real mailbox and alias to the target before importing data.
3. Confirm `10.0.188.14` and `fd7a:115c:a1e0:188::14` are unallocated.
4. Verify the LMTP listener is reachable only from `stalwart-edge` and that
   edge-produced Authentication-Results and spam classification survive local
   delivery unchanged.
5. Test Pocket ID end to end before depending on it. The OIDC directory is
   staged but intentionally described as dormant because the current Stalwart
   0.16 community web flow has not been proven.
6. Render and validate this directory and perform an isolated backup restore.
7. Add `apps/stalwart` to the root `kustomization.yaml` only when deployment
   is intentionally authorized.

No existing consumer, DNS record, router rule, or legacy Stalwart resource is
changed by this staging directory.
