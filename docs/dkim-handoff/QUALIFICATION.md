# Local qualification results

The executable suites use no production endpoints, credentials, records,
accounts or mail. All three suites ran in a fresh network namespace with only loopback.
All databases, generated keys, provider state and compiled fixtures were under
`/tmp`; the tests remove their temporary directories on exit.

## Passed

- `test_handoff.py`: **9 tests passed, no skips**.
- Real OpenTofu **1.11.5 and 1.12.1** and Cloudflare provider **5.22.0**, using a loopback
  fake API: Phase 0 plans two updates, uses PUT on unchanged record IDs, and
  preserves the unrelated fixture record.
- Phase 0's actual HCL expression matches the compiled `txt_chunks_to_text`
  function extracted from pinned **dns-update 0.5.7**, including RSA's quoted
  multi-chunk API content. The dependency's Cloudflare encoder calls that
  function with a single-space separator.
- Real provider moved/removed handoff: two forgets, no API mutations, unrelated
  state retained, subsequent plan clean.
- Custody preflight, masked readback, unchanged submitted bytes, mismatch
  rejection before writes, partial/ignored writes, explicit apply gates,
  HTTPS/redirect restrictions, and error-output redaction.
- Sequential inactive patches apply cleanly to temporary copies. Resend's
  configuration remains byte-identical.
- `native_fixture.py`: real **OSS Stalwart 0.16.21** accepts File -> Text,
  returns `{"@type":"Text","secret":"****"}`, retains the same derived
  public keys after restart with both fixture key files removed, and accepts
  an idempotent retry. Recovery-only fixture; no Account or mail listener.
- `signing_fixture.py`: approved-binary normal-mode File-backed RSA and Ed25519
  signing, then Text-backed signing after key-file removal/restart. Both native
  receiver verifications pass; separately corrupting each signature makes only
  that signature fail. IDs, selectors and public keys remain unchanged. The full
  proof passed on repeat execution. Host-network and wrong-binary
  refusal were also checked.
- Current and fully staged DNS/Stalwart Terraform configurations: offline init,
  format checks and validation passed using 1.11.5 and installed provider mirrors.
- Kustomize/kubeconform rerun: 99 valid, 0 invalid, 0 errors, 0 skipped.
- `nix fmt -- --fail-on-change`: 0 changes. `nix flake check --show-trace` passed
  for the current x86_64-linux system.
- `git diff --check` passed. Shared files were not modified.

Final native qualification used the approved deployment artifact at
`/tmp/stalwart-edge-qualification/stalwart`:

SHA-256: `02030a8334e3bc62bae1fa4a9139f498df0a7e105bd97ec5beacfdfa1be8b614`.
The fixture checks this hash before executing the binary. The initial local
Nix build was not accepted as deployment qualification; the complete native
fixture was rerun successfully with the approved artifact. No image was rebuilt
or changed.

## Deployed runner identification

A read-only HelmRelease audit confirmed the configured runner image index:
`ghcr.io/flux-iac/tf-runner:v0.16.5@sha256:7209171093907ec1d0559c682949fcee4b625205a6a058c16fe0ce0017af5f41`.
The cluster nodes are amd64. Its amd64 manifest is
`sha256:0bcc3b0aefe7a01d0ef998aa75163d341580712b327b8e136bf9167e6e0a322b`.
After verifying the image layer digest, the extracted `/usr/local/bin/tofu`
reported **1.12.1**, binary SHA-256
`b6cb308bd699c8b53882319986f339eeaa44f925a68f12d5b0a14e6caceedf23`.
The full fake-Cloudflare qualification passed with that binary as well as 1.11.5.
This identifies the configured image; it is not an exec into a running runner.

OpenTofu 1.12 ignores `required_version` in `.tf` files as a Terraform constraint;
the existing `~> 1.11.5` therefore does not pin the controller's OpenTofu version.
Do not infer the executable version from that declaration.

## Production preflight (2026-09-18)

Read-only checks now confirm exact Cloudflare API quoted-chunk content and native
public-key equality for both selectors. Both authoritative nameservers return
the matching TXT data. Current IDs/fingerprints and the limits of this check are
recorded in `production-preflight.json`; this is not an audit of the earlier
normalization mutation.

The dedicated backend Cloudflare credential is still absent, and the existing
management credential still lacks `taskDnsManagement`. No token was created,
permission expanded, owner released, key imported or publication enabled. Keep
both owners and mounted keys intact until those prerequisites are satisfied.

## Still required before advancing stages

1. Controller/source-revision coordination and reviewed real plans using the
   identified runner image. No in-cluster plan/apply was requested by these tests.
2. Recheck the observed Cloudflare IDs, exact native quoted-chunk API content,
   authoritative TXT and native public keys immediately before transfer, then
   verify unchanged IDs afterward. DNS semantic equality alone is insufficient.
3. A dedicated Cloudflare token scoped to the company zone, securely provisioned
   to the backend, plus the missing `taskDnsManagement` permission. Read-only
   permission discovery used the existing management credential; no DKIM private
   key or Cloudflare credential was read.
4. Both ownership-release receipts before importing any production key.
5. Production Text/metadata/public-key checks and restart verification before
   considering the old mounted dependency retired.

Automatic rotation is excluded, not qualified by these results. See README.md
for the known source failure path. No pushes, deployments or production
mutations have been made by this implementation task.
