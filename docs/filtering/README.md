# Inactive backend filtering stages

These patches are **not active configuration** or deployment authorization.
Filtering changes remain only in these patches. After explicit approval, promote
one patch at a time from the repository root and let tf-controller apply it
in-cluster. Never run a local production plan/apply.

## Trust boundary

Stage 20 deliberately removes the qualified fixture's exact-peer-IP predicate.
Changing IPv6 pod addresses are not identities. Production requires both:

- Existing Cilium ingress on backend port 24 restricted to the same endpoint's
  `io.kubernetes.pod.namespace=stalwart-edge` and `app=stalwart-edge` labels.
- DATA-stage spam filtering true only for `listener == 'edge-lmtp'`, false
  otherwise. Other SMTP paths retain their authentication requirements.

The native spam-rule context has no listener variable. Do not substitute an IP
or CIDR, expose LMTP, or enable these Header rules on another SMTP path. Every
mapping/credit requires a complete canonical enum-valued `X-Edge-Auth` header.
The edge replaces incoming copies and removes incoming `Authentication-Results`;
ARC headers are untouched.

Read-only checks on 2026-09-17 verified edge TLS+QUIT on port 24;
`uptime-kuma` verified TLS on 465 but timed out on 24. No MAIL, RCPT or DATA commands were sent.
No additional clusterwide policy selected the backend. Recheck before activation.

## Ordered promotion

Follow the personal repository's
[readiness sequence](https://github.com/michaelbrusegard/infra/blob/main/gitops/espresso/apps/stalwart-edge/FILTERING.md)
(local: `~/Projects/infra/gitops/espresso/apps/stalwart-edge/FILTERING.md`).
Readiness and edge configuration belong to the personal repository.

1. Read only `id`, `@type`, `tag` and `score` for `jdzlxyqedpaa`. Require the
   expected `BLOCKED_DOMAIN` Reject object; if it is already Score1000, skip the
   conversion. Stop on any other state. Through an approved administrative path,
   POST `convert-blocked-domain.json` to native `/jmap`. Confirm per-object success
   and read back `jdzlxyqedpaa` as
   `{"@type":"Score","tag":"BLOCKED_DOMAIN","score":1000}`. Preserve its ID.
   Conversion requires `tag`; later same-variant patches must omit that immutable
   field. Terraform's variant check rejects a Score import before conversion.
2. Promote **`stages/10-backend-safety.patch`**. This imports safety settings and
   the converted tag: thresholds 5/0/0, contact/reply trust retained, Pyzor off,
   LLM disabled, rule URL pinned to v3.0.1. Private LMTP filtering stays off.
   Verify no Reject/Discard tags and no changes to existing Score weights.
3. Deploy personal readiness in **`legacy`**. Grant only `sysMtaStageDataGet` and
   `sysSenderAuthGet` additionally to the existing readiness reader through an
   approved one-off administrative path; preserve existing permissions and verify
   reads with its actual credential. Switch to **`prepare`** before installing
   the exact qualified DATA script. Bind it with relaxed SPF/DKIM/DMARC while edge
   filtering remains on; verify runtime operation after a controlled restart.
   **Then snapshot edge queue IDs and wait for every message in that snapshot to
   leave the queue while backend filtering is still off.** Old queued messages
   may already contain attacker-written, syntactically valid `X-Edge-Auth`.
   Merely enabling the producer does not sanitize them. The restart closes old
   SMTP sessions; subsequent mail uses the new producer. Use queue metadata only,
   never message bodies. Prefer an unfiltered queue query returning `ids: []`
   and `total: 0` after restart (personal `filtering-stages/queue-empty-request.json`).
   A partial page is not a complete snapshot. Without a complete drain proof,
   do not enable the bridge.
   Do not rerun bootstrap or mount writer credentials in the pod.
4. Promote **`stages/20-auth-bridge.patch`**. It adds `filtering-bridge.tf` and
   `filtering-bridge.json`: seven Header rules, `EDGE_AUTH_VALID=0`, and
   `EDGE_DMARC_NA_OFFSET=-1`. Original authentication weights remain unchanged.
   It imports/overrides existing `STWT_AUTH_NA`, ID `jdzlxyp2ataa`, at priority
   1004. Validated headers supply actual `AUTH_NA`/`AUTH_NA_OR_FAIL`; the native
   rule remains the fallback for absent, malformed or untrusted summaries.
   There is no numeric AUTH_NA offset. Private LMTP filtering is still off.
5. Verify the producer/readiness, rules, IDs, tags, thresholds, and Cilium boundary.
   Existing `SenderAuth` already disables checks on private LMTP. These patches
   preserve it, unrelated listeners/routes, throttle/abuse exclusions and 1ms wait.
   Restart the backend while private-LMTP filtering is still off, then verify
   the persisted safety settings and rules again. API readback or provider reload
   warnings alone do not prove that old Reject actions left the runtime cache.
   Then promote **`stages/30-enable-private-lmtp.patch`**. It changes only the
   existing DATA-stage filter expression: `edge-lmtp` true, else false, with an
   explicit dependency on the completed rule configuration.
6. Verify native readback and authorized deliveries: clean and SPF-fail/DKIM-pass
   forwarding to Inbox; GTUBE and a real blocked-domain hit to Junk; no spam
   rejection/discard; queue drain. Older queued mail without a summary receives
   no fabricated authentication credit. Only then disable personal edge content
   filtering, tighten readiness to **`backend`**, and repeat restart/delivery
   checks. Do not leave `prepare` as the final state.

For rollback, switch readiness to `prepare` first. Then restore and verify
qualified edge filtering, and only then disable backend private-LMTP filtering
through an approved change. Keep
Junk-only safety settings. Blind patch reversal can leave both filters off or
restore Reject actions on an already-accepted delivery path.

## Qualification and limits

`qualification.json` freezes `/tmp/stalwart-edge-wdr7djqy`: 21 passing native
stages and 20 deliveries on approved binary SHA256
`02030a8334e3bc62bae1fa4a9139f498df0a7e105bd97ec5beacfdfa1be8b614`.
Coverage includes malformed trusted-peer headers, genuine SPF/DKIM/DMARC,
authenticated/unauthenticated bounces (including a real null envelope), a DKIM
DNS error, forged-header removal, GTUBE, blocked-domain lookup, in-place Reject
conversion, and exactly-once queue delivery through restarts of both native
processes. Fresh post-restart mail still produces verdicts and reaches Junk.
The unfiltered queue query also returns `ids: []` and `total: 0`.
It is not production delivery qualification.

Public v3.0.1's 403 tags/66 rules exactly match sanitized production metadata by
name and complete object value. The public fixture and MIT license are bundled in personal `packages/stalwart-oss/fixtures/`. This stage does not recreate
that inventory. The updater currently skips existing primary-key conflicts,
preserving overrides; recheck on upgrades. The release URL is version-pinned,
not content-addressed, so upstream asset replacement remains a trust risk.

Remaining limitations:

- Native DMARC-pass state and DMARC-gated contact ham trust/learning are not
  restored. Separate trusted-reply behavior remains enabled and can override
  spam placement, even at high scores; a trusted-reply history match was not tested.
- Protocol NA tags remain. DMARC_NA's score is compensated, but future rules
  consuming these tags need review. The AUTH_NA override fixes the demonstrated
  BOUNCE_NO_AUTH interaction.
- Original-client IP/EHLO reputation, ARC and DKIM2 results are not transported.
  Header removal can invalidate signatures covering those headers; the backend
  trusts edge verification rather than re-verifying.
- The production trained classifier was not exported/tested. Mailbox rules,
  quotas and recipient changes can still cause delivery failures.

Resend and Manata are outside this rollout.

## Offline checks

```sh
python -B docs/filtering/test_filtering.py -v
python -B docs/filtering/validate.py --tofu /tmp/tofu-runner-qualified-tofu
```

The validator pins the controller-extracted **OpenTofu 1.12.1**, SHA256
`b6cb308bd699c8b53882319986f339eeaa44f925a68f12d5b0a14e6caceedf23`, not 1.11.5.
It uses the installed `tahacodes/stalwart` 0.2.3 provider (`--provider-dir` can
select an existing matching directory). Its verified release ZIP SHA256 is
`9b4b3dc07a73055d7116fc426c6009de86479df7776ab23b6795132eeca8c119`;
the extracted binary SHA256 is
`58bbac53de7ab857503c833ae5049915c2f015f72bf7b6aec99e889dd68684e1`.

It copies only stack `.tf` files and the lockfile into fresh `/tmp` storage,
uses an offline provider mirror and separate user/network namespaces, strips
credential environment variables, and substitutes an unreachable loopback endpoint.
It runs `init -backend=false` once, then `fmt -check` and `validate` after each stage.
No production state is read/copied; no plan/apply/import is invoked. Evidence stays
in the printed directory. `validation.json` records the passing run; changed
sources or patches require revalidation.
