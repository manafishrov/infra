# Manafish DKIM custody and publication handoff

Only Phase 0 is active configuration. The files in `stages/` are unapplied,
sequential patches, not Terraform modules or a deployment script. Do not apply
all patches together. Each stage needs its predecessor's production evidence
and separate rollout approval. OpenTofu runs through the consumer's controller,
not against production from a local checkout.

Scope: preserve the existing two keys and selectors, move private-key custody
into Stalwart, and let Stalwart publish only their DKIM TXT records. Keep DKIM
rotation **Manual**, certificate management Manual, and `nextTransitionAt=null`.
No Resend, router/DDNS, Pocket ID/SCIM, edge, or backup changes are included.

## Why Phase 0 is separate

Stalwart 0.16.21 generates these exact strings:

- `v=DKIM1; k=rsa; h=sha256; p=<existing-public-key>`
- `v=DKIM1; k=ed25519; h=sha256; p=<existing-public-key>`

The old records omitted `h=sha256`. In addition, `dns-update` 0.5.7 encodes TXT
API content as quoted chunks of at most 255 bytes, joined by one space. RSA
crosses this boundary; Ed25519 usually fits in one chunk. Matching only decoded
DNS text is insufficient. The publisher matches encoded content exactly and
deletes unmatched records **before** creating replacements. Turning publication
on first could remove working records and then fail to recreate them.

Phase 0 changes only those two contents while OpenTofu still owns them. Provider
5.22.0 updates an existing record ID with **PUT**, not PATCH or delete/create.
The local provider test exercises that actual binary against a loopback fake API.
It does not prove Cloudflare's real-world response encoding or propagation.

## Gates and patches

Before releasing either owner, have the dedicated zone credential provisioned
and the required native permission grants verified. Credential provisioning and
the environment restart described in stage 3 can happen earlier while File keys
and OpenTofu DNS ownership are still intact. Do not start an ownership gap while
waiting for credentials.

### 0. Normalize with the current owner

Active edits: `tofu/dns/main.tf` adds `h=sha256` and renders the exact quoted
255-byte Cloudflare chunks. `tofu/dns/variables.tf` restricts the existing public
inputs to single-line standard base64, making character slicing byte-exact for
this ASCII-only text. Public key material is unchanged.

Before approving the controller plan:

- Capture the two Cloudflare record IDs and current public values. Read only
  these records; do not export the whole state or credentials into a report.
- Compare each `p=` to the corresponding native `DkimSignature.publicKey`.
- Require exactly two content updates in place, zero replacements/deletes,
  and no unrelated changes. Names, selectors, record types and TTLs stay put.

After application, require unchanged record IDs and Cloudflare API `content`
byte-for-byte equal to the expected quoted-chunk representation, including its
quotes and separating spaces. Separately compare authoritative DNS TXT data
with chunks decoded and joined in order. Wait out the old TTL before progressing.
If Cloudflare rewrites that API representation differently, stop: semantically
identical DNS is not sufficient for a delete-free handoff. Both public keys must
match native output; do not assume the Terraform inputs are already equivalent.

### 1. Release both owners without deleting anything

Only after gate 0, review `stages/10-release-ownership.patch`:

- Remove the two standalone Stalwart key resources and their import blocks.
  Add `tofu/stalwart/handoff.tf` with `removed`/`destroy=false` for each resource.
- Remove only `stalwart_dkim_rsa` and `stalwart_dkim_ed25519` from the DNS
  `for_each` map. Remove their now-unused public-key variables.
- Add `tofu/dns/handoff.tf`: move each selected Cloudflare instance to its own
  unkeyed address, then forget that address with `destroy=false`.

OpenTofu 1.11.5 rejects an instance key directly in `removed.from`. The combined
`moved` -> unkeyed `removed` plan is tested, so no manual state-forget is needed
unless the exact installed controller fails this qualification. Never forget
all of `cloudflare_dns_record.manafishrov`.

The two consumer Terraform resources are independent and normally auto-approve.
The operator must prevent concurrent/stale applies and review the exact source
revision and plan for each. Do not resume an old configuration after the forget:
it could recreate ownership or revert the custody change.

Each stack's plan must contain exactly two forgets, zero remote mutations and
no unrelated changes. Confirm both stacks finished, remote IDs/records still
exist, and no DKIM imports remain. Coordinate removal of the two obsolete public
values from the consumer's `varsFrom` source. Do not read or edit its secrets as
part of this repository change.

### 2. Import the exact mounted bytes through the native API

Use `custody.py` only after gate 1. It is a small, one-time tool, not a reconciler.
It never obtains Kubernetes Secrets or decrypts SOPS. An authorized operator
must supply the existing PEM bytes in memory as a JSON object on stdin:
`{"rsa": "<existing PEM>", "ed25519": "<existing PEM>"}`. Do not write that
JSON to disk, put keys in arguments, or use shell tracing. Supply the dedicated
management token through `STALWART_TOKEN` in the process environment.

The endpoint must be the private management **HTTPS origin**. Certificate and
hostname verification are mandatory; `--ca-file` can supply a private CA.
Redirects and inherited HTTP proxies are disabled. No HTTP fallback is provided.

```text
python3 -B docs/dkim-handoff/custody.py --endpoint <private-HTTPS-origin>
python3 -B docs/dkim-handoff/custody.py --endpoint <private-HTTPS-origin> \
  --apply --ownership-released --phase0-verified
```

Both invocations read their input from the authorized in-memory producer. The
first is read-only; the second explicitly imports. The confirmation flags are
operator attestations, not proof that Terraform ownership has been released.
Never invoke the write form merely because the flags are available.

The tool is bound to domain `c` (`manafishrov.com`) and the existing key IDs:

| ID | Algorithm | Selector |
| --- | --- | --- |
| `jdzlxs2ualqa` | RSA | `stalwart-rsa` |
| `jdzlxs2uamqa` | Ed25519 | `stalwart-ed25519` |

It checks both keys and their metadata before writing either, compares derived
public keys using OpenSSL, and replaces only the complete `privateKey` union
with `{"@type":"Text","secret":...}`. `Text`, not `Value`, is the native
variant. No stripping or newline conversion is performed on the submitted PEMs.
Native readback masks the secret as `****`: the tool checks `@type: Text`, no
remaining file/environment reference, and unchanged derived public keys and
metadata. It never expects plaintext readback. This proves key identity and
custody form, not the byte formatting of masked stored PEMs. Its receipt contains
only IDs, selectors and public-key fingerprints.

Native Set can partially succeed. There is no automatic retry or rollback. On
any error retain the mounts, inspect both keys using the private API, and rerun
the check after resolving the cause. Reapplying the same keys is idempotent.
Do not attempt recovery by resuming the old Terraform key resources.

Python does not guarantee memory zeroization. Run in a trusted operator process;
core dumps are disabled. Native database custody requires appropriate protection
of the existing persistent store. This procedure does not inspect or change any
backup system. No private key belongs in Terraform configuration, state, a plan,
a log, or a support artifact.

### 3. Configure the dedicated Cloudflare credential and provider

Credential issuance is an external prerequisite, not automated here:

- Zone: only `manafishrov.com`.
- Zone Read and DNS Edit/Write, sufficient for listing and changing DNS records.
- No global API key and no reuse of the shared controller's broad token.

Cloudflare's zone token is not restricted to the two selectors. `publishRecords`
and the native signature inventory are operational limits, not a token ACL.
Verify that the domain's complete native DKIM inventory contains only the two
approved selectors. A future native signature could otherwise add publication
ownership, including a conflicting selector.

The consumer operator supplies the token under
`STALWART_CLOUDFLARE_DKIM_TOKEN` in the backend's existing `stalwart-env` Secret
through its encrypted-secret workflow. A pod must restart to acquire a changed
environment. Keep the DKIM mount at this point. Never pass the Cloudflare token
as a Terraform variable.

Then review `stages/20-configure-provider.patch`. It adds the existing provider's
`stalwart_dns_server_cloudflare.dkim`, referring to `EnvironmentVariable`.
The backend must already see that variable: native provider validation resolves
it. This stage does not change the Domain or schedule publication.

### 4. Enable only DKIM publication

Before applying `stages/21-enable-publication.patch`, recheck normalized
Cloudflare API contents and IDs against native public keys. Do not proceed on
extra/conflicting TXT values; reconciliation owns the whole selector TXT RRset.

The patch changes only the Manafish Domain's `dns_management`: Automatic,
origin `manafishrov.com`, and `publish_records=["dkim"]`. DKIM and certificates
remain Manual. The internal system Domain is unchanged.

Manual -> Automatic DNS schedules an initial `DnsManagement` task even with
DKIM Manual. Inspect that task and both public records. Existing exact content
should cause no Cloudflare mutation. Do not treat a successful Domain update as
proof that asynchronous publication succeeded.

A later key edit or edit of an already-Automatic DNS configuration does not
necessarily schedule another publication. `refresh-request.json` is a passive,
public-data native `/jmap` request for an explicit DKIM-only refresh. Use the
existing authenticated API/CLI workflow only when a refresh is needed. Inspect
`notCreated` and task completion; an HTTP 200 alone is not success. Provider
0.2.3 does not expose a DNS-management task resource. No periodic drift repair
or new service is introduced by this handoff.

Do not create `DkimManagement` tasks. Do not schedule a rotation or change stage
or `nextTransitionAt`. Do not enable automatic certificates.

### 5. Remove the mounted dependency

After successful custody readback/publication, review
`stages/30-remove-key-mount.patch`. It removes only the DKIM mount, volume and
reloader reference from the StatefulSet. TLS and other secrets are unchanged.
Retain the original Secret only until this restart is verified. After the
rollout, verify native Text key readback, unchanged derived public keys,
Active/null metadata, healthy backend readiness, and clean Terraform plans.
No email test or DATA probe is required or included.

### 6. Retire the obsolete Secret

After the no-mount restart passes, remove only the `stalwart-dkim` Secret
document from the private secrets repository's `apps/stalwart/secrets.yaml`.
That file also contains `stalwart-env`; preserve its Resend credential and the
new Cloudflare credential. Use the repository's SOPS workflow without writing
plaintext keys to disk. Let Flux prune the obsolete Kubernetes Secret and
verify that it is absent. Do not leave it in active reconciliation as a second
key source. Encrypted Git history remains untouched; no backup or Manata access
is part of this cleanup.

## Native API permissions

Use the existing machine principal; no human admin or new account is required.
Both the principal and API-key scope must permit the requested operation.

- Custody tool: `sysDomainGet`, `sysDkimSignatureGet`, `sysDkimSignatureUpdate`.
  Discovery outside the tool additionally needs `sysDkimSignatureQuery`.
- Terraform DNS provider: `sysDnsServerGet`, `sysDnsServerCreate`,
  `sysDnsServerUpdate`; Query if used for discovery. Destroy is not needed for
  this rollout and should remain a separate approval.
- Domain configuration: `sysDomainGet`, `sysDomainUpdate`.
- Explicit publication: `sysTaskCreate` **and** `taskDnsManagement`;
  `sysTaskGet`/`sysTaskQuery` to inspect results.

A read-only audit of the deployed backend token found the required registry
permissions present, but **`taskDnsManagement` absent**. Approve and verify that
narrow grant before using the explicit refresh request. A document change does
not expand an existing principal or API-key scope. Do not assume `sysTaskCreate`
alone authorizes DNS publication.

Do not add DKIM Create/Destroy or `taskDkimManagement`. Native DNS tasks trust
`updateRecords` rather than intersecting it with `publishRecords`; keep task
creation credentials tightly scoped operationally.

## Local qualification

No test below uses a production account, DNS zone, mail connection or credential.
The custody tests use ephemeral generated keys and a fake native API. The
provider test uses OpenTofu 1.11.5 and/or the runner's 1.12.1 binary, plus real
Cloudflare provider 5.22.0 against a
loopback fake API, with only dummy tokens and a temporary local backend.

```sh
python3 -B docs/dkim-handoff/test_handoff.py -v
TOFU_1_11_5=/path/to/tofu-1.11.5 \
TOFU_RUNNER_1_12_1=/path/to/runner-tofu-1.12.1 \
CF_PROVIDER_MIRROR="$PWD/tofu/dns/.terraform/providers" \
DNS_UPDATE_SOURCE=/path/to/dns-update-0.5.7 \
RUSTC=/path/to/native/rustc \
CHECKPOINT_DISABLE=1 python3 -B docs/dkim-handoff/test_handoff.py -v
```

For the provider test also set `DNS_UPDATE_SOURCE` to the pinned `dns-update`
0.5.7 source directory and `RUSTC` to a working native compiler (with a linker
on PATH). It compiles the actual `txt_chunks_to_text` function into a temporary
fixture and compares provider API contents against it, including multi-chunk RSA.
The provider test requires an already-installed mirror; it does not download
providers or use the production module/backend. It asserts:

- Phase 0 plans only two content updates and issues PUTs to the same record IDs.
- The moved/removed handoff issues no API mutation and leaves the Resend-like
  resource managed. The subsequent plan is clean.
- Custody submits only Text, preserves input PEM bytes (including CRLF), accepts
  masked native readback, rejects metadata/public-key mismatch before any write,
  and detects partial/ignored writes. Receipts contain no private material.
- All later patches apply in order to temporary copies; only Phase 0 is active.

There is also a real native-binary fixture, run only in a fresh Linux network
namespace with loopback as its sole interface:

```sh
unshare --user --map-root-user --net sh -c '
  ip link set lo up
  exec python3 -B docs/dkim-handoff/native_fixture.py --binary /path/to/stalwart
'
```

It requires the approved binary SHA-256
`02030a8334e3bc62bae1fa4a9139f498df0a7e105bd97ec5beacfdfa1be8b614`,
version 0.16.21 and OSS edition. It creates only an ephemeral local Domain
and generated DKIM keys (no Account), and uses isolated Recovery HTTP. It imports
File -> Text through the real API, asserts `secret: "****"`, removes the fixture
key files, restarts, rechecks both public keys and retries idempotently. No mail
listener or DNS provider is configured. The production helper still requires TLS.

`signing_fixture.py` additionally verifies actual outgoing signatures in normal
mode, using the existing personal-repository mail helpers:

```sh
unshare --user --map-root-user --net sh -c '
  ip link set lo up
  exec python3 -B docs/dkim-handoff/signing_fixture.py \
    --binary /path/to/approved/stalwart \
    --fixture-directory /path/to/personal/infra/packages/stalwart-oss
'
```

It requires `named`, `openssl` and `ip`. Two approved native instances exchange
disposable mail over TLS LMTP against isolated authoritative DNS. Both original
selectors verify before migration and after Text custody, removal of key files,
and normal-mode restart. Independently corrupting each signature makes only that
signature fail at the native receiver. The fixture verifies the new receiver's
Authentication-Results, never an older replayed result. Generated fixture
credentials/accounts/mail stay inside the disposable namespace.

Local native persistence and masked readback are tested; the running production
image and credential scope still need the operator gates above. The tests do not
qualify a live controller plan or real Cloudflare's TXT canonicalization. The
configured runner image contains OpenTofu 1.12.1, and its extracted binary passed
the same tests; see QUALIFICATION.md for image and binary digests. OpenTofu 1.12
ignores `required_version` in `.tf` files, so the existing `~> 1.11.5` declaration
is not an OpenTofu pin. General version-constraint cleanup is outside this handoff.

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
- [Native SecretText variants](https://github.com/stalwartlabs/stalwart/blob/v0.16.21/crates/registry/src/schema/structs.rs#L4687).
- [Cloudflare permission reference](https://developers.cloudflare.com/fundamentals/api/reference/permissions/).

Automatic rotation remains excluded: the inspected 0.16.21 task can move old
Active keys to Retiring even if replacement publication fails. Existing Active
keys with null transition times also do not acquire a schedule simply by enabling
Automatic. This handoff does not attempt to solve either rotation behavior.
