# DKIM qualification and production evidence

Production handoff is complete. The local fixtures below qualify specific API,
provider and custody behavior; production receipts establish what happened to
the deployed keys and records. These are separate claims.

## Production handoff (2026-09-18)

The production rollout completed these checks. See
[production-handoff.json](production-handoff.json) for the final receipt:

- Both reviewed controller release plans at `1ca2634715` contained exactly two
  forgets and zero remote mutations per stack.
- Native File-to-Text import preserved the existing keys and public-key identity.
- Provider revision `3e1bcc0ebb` created one Cloudflare provider referencing
  `STALWART_CLOUDFLARE_DKIM_TOKEN` as an EnvironmentVariable, not a token in state.
- Domain revision `606a4c7162` changed only DNS management to Automatic,
  `publish_records=["dkim"]`, origin `manafishrov.com`.
- Native `dns.record-created` success events were observed at
  `2026-09-18T11:52:36Z` for Ed25519 and `11:52:37Z` for RSA. Cloudflare IDs and
  exact contents remained unchanged; the event name does not imply recreation.
- Mountless rollout `49aa97f` restarted successfully. Native readback retained
  Text custody, active/null metadata and the same public keys.
- The obsolete DKIM Secret was removed from active company SOPS and the live
  cluster. Original encrypted Git history remains preserved.
- The narrow permission grant was denied and original principal permissions
  stayed unchanged. Initial publication used normal native automatic scheduling,
  not explicit task creation or a recovery-mode authorization workaround.

[production-preflight.json](production-preflight.json) remains the historical
read-only preflight of exact API contents, authoritative TXT and native public
keys. It is not an audit of the earlier normalization mutation and is not the
final handoff receipt. No new production access was performed for this docs/test
cleanup.

## Refreshed tests

`test_handoff.py`: **12 tests passed, no skips** with both OpenTofu **1.11.5** and
runner **1.12.1**, Cloudflare provider **5.22.0**, and pinned **dns-update 0.5.7**.
The full run used a fresh user/network namespace with only loopback. Keys,
provider state, compiler output and fake API data were temporary and removed on
exit. No production endpoint or credential was used.

The refreshed suite checks:

- Final repository configuration: no Terraform-managed native DKIM keys/imports
  or old selector map entries/public-key variables; both stacks retain exactly
  two non-destructive release declarations; Manual rotation/certificates;
  DKIM-only Automatic DNS with the intended origin/provider; environment-only
  provider secret reference; no old DKIM mount/reloader reference, TLS retained.
- A self-contained historical normalization HCL fixture with fake public keys,
  independent of the now-removed Phase 0 active locals/variables. Its output
  matches the compiled native `txt_chunks_to_text` dependency function, including
  RSA's quoted multi-chunk representation and the single-space separator.
- Real provider/OpenTofu plans two updates, issues exactly two PUTs on unchanged
  IDs, then plans/applies exactly two forgets without API mutations. The
  Resend-like record and its managed state remain unchanged; the final plan is
  clean. This fake API cannot establish real Cloudflare response encoding.
- Custody preflight, unchanged submitted PEM bytes, masked readback, mismatch
  rejection before writes, partial/ignored writes, explicit apply gates,
  HTTPS/redirect restrictions and error-output redaction.

Without the optional environment, the same invocation reports **11 passed and
one provider test skipped**, with the explicit reason:
`set a qualified TOFU binary, CF_PROVIDER_MIRROR, DNS_UPDATE_SOURCE and RUSTC`.
The full run below had no skips. Repository assertions inspect configuration;
they do not inspect secret values or prove live Text/active/null metadata.

### Exact full-provider invocation used

Run from the company checkout root. These are local qualification artifact
paths, not production configuration inputs:

```sh
unshare -Urn sh -c '
  ip link set lo up
  exec env \
    TOFU_1_11_5=/tmp/dkim-handoff-tofu.SuiBRp/bin/tofu \
    TOFU_RUNNER_1_12_1=/tmp/tofu-runner-qualified-tofu \
    CF_PROVIDER_MIRROR="$PWD/tofu/dns/.terraform/providers" \
    DNS_UPDATE_SOURCE=/nix/store/ypbl9b0fsiwzkx2lka84a9mss1bc9q6h-stalwart-native-scim-0.16.21-vendor/source-registry-0/dns-update-0.5.7 \
    RUSTC=/nix/store/wnhmqix7bippbbzasj29qiyb422g9asg-rustc-wrapper-1.95.0/bin/rustc \
    CHECKPOINT_DISABLE=1 python3 -B docs/dkim-handoff/test_handoff.py -v
'
```

The provider subprocess uses a sanitized environment, dummy token and local
backend. The mirror must already exist; tests do not download a provider.

## Retained native qualification

The approved deployment artifact is OSS Stalwart **0.16.21**, SHA-256
`02030a8334e3bc62bae1fa4a9139f498df0a7e105bd97ec5beacfdfa1be8b614`, locally at
`/tmp/stalwart-edge-qualification/stalwart`. The native fixtures reject a different
hash. No image or binary was rebuilt or changed for qualification.

Previously completed native runs, not rerun in this docs/test cleanup:

- `native_fixture.py`: real File-to-Text API import, masked secret readback,
  unchanged public keys after removal of generated key files/restart, and
  idempotent retry. Recovery-only disposable database, no Account/mail listener;
  not a restricted-authorization proof.
- `signing_fixture.py`: normal-mode RSA and Ed25519 signing before/after Text
  import, removal of fixture files and restart. Both native receiver verifications
  pass; separately corrupting either signature fails only that signature. IDs,
  selectors and public keys remain unchanged. Repeated successfully; host-network
  and wrong-binary refusal were also checked. Generated fixture mail only, not
  production mail delivery.
- `dns_authorization_fixture.py`: reusable CLI passed twice with the approved
  binary. Fresh user/network namespaces, loopback only; recovery used solely for
  provisioning. All authorization assertions run after a normal-mode restart.
  The caller has `sysDomainGet/Update`, `sysTaskGet/Query/Create`, and explicitly
  disabled `taskDnsManagement`. Explicit task creation is forbidden; initial
  Manual-to-Automatic DNS schedules exactly one DKIM-only task with
  `onSuccessRenewCertificate=false`. Manual DKIM/certificates remain unchanged;
  an unchanged Automatic update adds no task. The real native provider dispatch
  ends in an expected isolated Cloudflare transport failure, not publication
  success. Production API-key inheritance is not modeled by that fixture.

The earlier implementation also recorded offline Terraform validation,
Kustomize/kubeconform (99 valid), Nix formatting/flake checks and staged-patch
application tests. Those are historical results, not checks of this cleanup.
Applied stage patches are now removed and final-state assertions replace the
patch-application test. Final rollout checks passed: the full 12-test suite
with no skips, `nix fmt`, `nix flake check --show-trace`, both OpenTofu format
checks, and root Kustomize/kubeconform validation (97 valid, zero errors/skips).
Both authoritative servers also matched both native public keys after the
mountless restart.

## Deployed runner identification

The earlier read-only HelmRelease audit identified image index
`ghcr.io/flux-iac/tf-runner:v0.16.5@sha256:7209171093907ec1d0559c682949fcee4b625205a6a058c16fe0ce0017af5f41`.
The cluster nodes are amd64; its amd64 manifest is
`sha256:0bcc3b0aefe7a01d0ef998aa75163d341580712b327b8e136bf9167e6e0a322b`.
After image-layer digest verification, the extracted `/usr/local/bin/tofu`
reported **1.12.1**, binary SHA-256
`b6cb308bd699c8b53882319986f339eeaa44f925a68f12d5b0a14e6caceedf23`.
This identifies the configured image, not an exec into a running runner. Its
extracted binary passed the refreshed fake-Cloudflare suite alongside 1.11.5.

OpenTofu 1.12 ignores `required_version` in `.tf` files as a Terraform constraint.
The existing `~> 1.11.5` declaration is not an OpenTofu runner pin; general
version-constraint cleanup is outside this handoff.

## Remaining limits

Automatic rotation is excluded, not qualified. There is no periodic drift repair.
Explicit manual refresh still needs an authorized administrator with
`sysTaskCreate` and `taskDnsManagement`; do not toggle domain configuration to
bypass that restriction. The [operations guide](README.md) retains source links,
exact-content hazards and runtime verification requirements.
