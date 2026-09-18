# Manafish DKIM operations

The production handoff is complete. Stalwart holds the existing private keys as
native Text secrets and publishes their DKIM TXT records. OpenTofu no longer
manages either key or either selector record. DKIM rotation and certificate
management remain Manual; both keys remain active with `nextTransitionAt=null`.

See [production-handoff.json](production-handoff.json) for the production
receipt and [QUALIFICATION.md](QUALIFICATION.md) for isolated test evidence.
[production-preflight.json](production-preflight.json) is the historical,
read-only preflight, not the final receipt. The applied stage patches have been
retired; Git history retains them. Do not replay the old rollout.

## Current ownership and safety limits

| Native key ID | Algorithm | Selector |
| --- | --- | --- |
| `jdzlxs2ualqa` | RSA | `stalwart-rsa` |
| `jdzlxs2uamqa` | Ed25519 | `stalwart-ed25519` |

The domain is `c` (`manafishrov.com`). Its DNS management is Automatic with
`publish_records=["dkim"]` and origin `manafishrov.com`. The Cloudflare provider
resolves `STALWART_CLOUDFLARE_DKIM_TOKEN` from the backend environment. The token
is not a Terraform variable or a plaintext repository value. A changed
environment credential requires a backend restart.

The `tofu/stalwart/handoff.tf` and `tofu/dns/handoff.tf` moved/removed declarations
retain the non-destructive ownership-release record (`destroy=false`). Do not
restore the old resources or imports: that would reintroduce competing owners.
All production OpenTofu work remains controller-managed, with reviewed plans.

The StatefulSet no longer mounts the DKIM Secret or includes it in its reloader
list. The old Secret was removed from active company SOPS and the cluster after
the mountless restart passed. Original encrypted Git history remains intact.
Native database custody requires protection of the persistent store; this
handoff did not qualify or change backups.

Keep these limits:

- Preserve the two key IDs, selectors and public keys. Do not create rotation
  tasks, alter stages/transition times, or enable automatic certificates.
- Audit the domain's complete native signature inventory before publication.
  An additional signature can expand the TXT records Stalwart publishes.
- Keep the dedicated credential scoped to the company zone with Zone Read and
  DNS Edit. Cloudflare's zone token is not restricted to the two selectors;
  `publishRecords` is an operational setting, not a token ACL.
- Leave Resend, router/DDNS, Pocket ID/SCIM and unrelated DNS ownership alone.

## Publication and refresh

Manual-to-Automatic DNS activation natively schedules the initial DNS task even
when DKIM rotation is Manual. The completed handoff used that normal API path.
Native publication events were observed at `2026-09-18T11:52:36Z` (Ed25519) and
`11:52:37Z` (RSA), with unchanged Cloudflare IDs and exact contents. These events
are not evidence that Cloudflare records were recreated; the API readback is the
identity/content check. The mountless rollout also retained Text/active/null
readback and the same public keys. Details belong in the production receipt.

There is **no periodic drift repair**. A key edit or an edit to already-Automatic
DNS settings does not necessarily schedule publication. Do not interpret a
successful Domain update or HTTP 200 as successful asynchronous publication.

[refresh-request.json](refresh-request.json) is a passive, public-data request
for a DKIM-only refresh. Explicit refresh requires an authorized administrator
or credential with both `sysTaskCreate` and `taskDnsManagement`;
`sysTaskGet`/`sysTaskQuery` allow inspection. Check `notCreated`, the task's terminal
status, exact Cloudflare API contents/IDs, and authoritative TXT data.

The existing machine principal lacks `taskDnsManagement`. The approved narrow
grant attempt was denied; its original permissions stayed unchanged. The
isolated normal-mode authorization fixture confirms that explicit task creation
is still forbidden while initial automatic scheduling is part of existing
`sysDomainUpdate` authority. No recovery-mode authorization workaround was used.
**Do not toggle domain settings to bypass the explicit-task permission.** A
future explicit refresh needs an already authorized administrator, not another
activation cycle or an unapproved privilege grant. Native DNS tasks trust
`updateRecords` rather than intersecting it with `publishRecords`; review the
request scope as well as the credential.

## Exact-content and custody checks

Stalwart 0.16.21 emits `v=DKIM1; k=<algorithm>; h=sha256; p=<public-key>`.
`dns-update` 0.5.7 represents Cloudflare TXT content as quoted chunks of at most
255 bytes, joined by one space. RSA crosses that boundary. The publisher matches
encoded API content exactly and deletes unmatched values before creating their
replacements. Decoded DNS equality alone is insufficient for a delete-free
refresh. Stop on unexpected or conflicting selector RRset values.

The earlier normalization used provider 5.22.0 PUT updates on existing record IDs
before ownership release. The retained provider test models that historical
transition using fake public data; active Terraform intentionally contains no
normalization variables or DKIM record resources.

`custody.py` remains a one-time migration/check tool, not a reconciler or a
routine recovery step. It checks both original keys and metadata before writing,
submits unchanged PEM bytes only as the native Text union, and accepts masked
readback (`{"@type":"Text","secret":"****"}`). Matching derived public keys
proves identity, not the exact formatting of a masked stored PEM. Do not print
private keys, put them in arguments, export them into Terraform, or recreate the
retired Secret to run this tool. Any future custody operation needs separate
approval and trusted in-memory input. Its apply flags are operator attestations,
not proof that release gates were met.

## Local qualification

```sh
python3 -B docs/dkim-handoff/test_handoff.py -v
```

Without provider environment variables, the real-provider test is explicitly
skipped. The remaining tests cover custody failure handling and the final checked-in
safety configuration, not live secret values or runtime key metadata.

For full provider qualification, use the exact local paths in
[QUALIFICATION.md](QUALIFICATION.md), or supply a qualified OpenTofu 1.11.5 and/or
runner 1.12.1 binary, installed Cloudflare 5.22.0 mirror, pinned `dns-update` 0.5.7
source and native Rust compiler. No downloads, real backend or production tokens
are needed. The test asserts two in-place PUT updates, two subsequent forgets
with zero API mutations, unchanged Resend-like data/state and a clean final plan.

The retained native fixtures require the approved OSS 0.16.21 binary, SHA-256
`02030a8334e3bc62bae1fa4a9139f498df0a7e105bd97ec5beacfdfa1be8b614`:

- `native_fixture.py`: isolated recovery-mode File-to-Text persistence and masked
  readback after removing fixture files/restarting. Not an authorization proof.
- `signing_fixture.py`: two normal-mode native instances verify RSA and Ed25519
  signatures before/after custody migration and restart. Independent tamper
  controls fail only the corrupted signature. Uses generated mail/keys only.
- `dns_authorization_fixture.py`: launches its own fresh user/network namespaces,
  provisions disposable data, then tests only in normal mode. A caller with
  `sysTaskCreate` but disabled `taskDnsManagement` is denied explicit creation;
  initial activation schedules exactly one DKIM-only task with certificate
  renewal false and Manual DKIM/certificates unchanged. The fake Cloudflare
  provider fails under isolation. It does not prove publication success or
  production API-key inheritance.

```sh
python3 -B docs/dkim-handoff/dns_authorization_fixture.py \
  --binary /path/to/approved/stalwart \
  --fixture-directory /path/to/personal/infra/packages/stalwart-oss

unshare --user --map-root-user --net sh -c '
  ip link set lo up
  exec python3 -B docs/dkim-handoff/native_fixture.py --binary /path/to/approved/stalwart
'
unshare --user --map-root-user --net sh -c '
  ip link set lo up
  exec python3 -B docs/dkim-handoff/signing_fixture.py \
    --binary /path/to/approved/stalwart \
    --fixture-directory /path/to/personal/infra/packages/stalwart-oss
'
```

The signing fixture also requires `named`, `openssl` and `ip`. Local fixtures do
not qualify controller plans, real Cloudflare canonicalization or production
mail delivery. Production evidence is recorded separately. The configured
runner's extracted binary is OpenTofu 1.12.1; `.tf` `required_version` is ignored
by OpenTofu 1.12 and is not a runner pin.

## Source evidence

- [Pinned native TXT generator](https://github.com/stalwartlabs/stalwart/blob/v0.16.21/crates/common/src/network/dkim.rs#L120): includes `h=sha256`.
- [Pinned Cloudflare provider update](https://github.com/cloudflare/terraform-provider-cloudflare/blob/v5.22.0/internal/services/dns_record/resource.go#L108)
  and [SDK PUT implementation](https://github.com/cloudflare/cloudflare-go/blob/v7.7.0/dns/record.go#L79).
- `dns-update` 0.5.7, `src/providers/cloudflare.rs:174-207,400-403` and
  `src/utils.rs:22-43`: exact-content matching, quoted chunk encoding, and
  delete-before-create for unmatched RRset values.
- Native `registry/src/schema/structs_impl.rs:35321-35325`: Text secret readback
  always emits `MASKED_PASSWORD`, defined as `****` in `schema/prelude.rs:58`.
- [OpenTofu 1.11 removal semantics](https://opentofu.org/docs/v1.11/language/resources/syntax/)
  and [instance-key rejection](https://github.com/opentofu/opentofu/blob/v1.11.5/internal/addrs/parse_target.go#L157).
- [Native DNS scheduling](https://github.com/stalwartlabs/stalwart/blob/v0.16.21/crates/jmap/src/registry/mapping/domain.rs#L102)
  and [DNS task implementation](https://github.com/stalwartlabs/stalwart/blob/v0.16.21/crates/services/src/task_manager/dns.rs).
- [Explicit task permission check](https://github.com/stalwartlabs/stalwart/blob/v0.16.21/crates/jmap/src/registry/mapping/task.rs#L73)
  and [domain-generated task dispatch](https://github.com/stalwartlabs/stalwart/blob/v0.16.21/crates/jmap/src/registry/set.rs#L639).
- [Native SecretText variants](https://github.com/stalwartlabs/stalwart/blob/v0.16.21/crates/registry/src/schema/structs.rs#L4687).
- [Cloudflare permission reference](https://developers.cloudflare.com/fundamentals/api/reference/permissions/).

Automatic rotation remains excluded: the inspected 0.16.21 task can move old
Active keys to Retiring even if replacement publication fails. Existing Active
keys with null transition times also do not acquire a schedule simply by enabling
Automatic. This handoff does not attempt to solve either rotation behavior.
