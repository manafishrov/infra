# Stalwart v0.16.27 to v1.0.3

Manual, offline migration on `data-stalwart-0`. Nothing in this directory is
referenced by a kustomization. These files are preparation, not a live rollout.
The operator must authorize the cluster operations below separately.

`data/` remains the v0.16 rollback store. `data-v1/` starts empty; migration
progress, answers and reports live alongside both at `migration-v1/`. Keep the
original state directory when resuming. Do not let either server run during
migration or start v1 on an empty target before the copy.

## Before the window

- Rehearse against a restored PVC snapshot with the patched v0.16.27 and v1.0.3
  builds. Confirm object IDs, SCIM restoration, OAuth login, DKIM custody and
  all listeners. The 97 MB source size is not a timing guarantee.
- Fill the server image tag/digest in `../statefulset.yaml`, the 2.x WebUI
  `resource_url` in `../../../tofu/stalwart/main.tf`, and the provider image
  tag/digest in the personal repo's runner. None of these placeholders deploys.
- Publish the provider/server artifacts before releasing the consumer changes.
  The provider lock includes the exact Linux image binary and the Darwin build;
  regenerate with `tofu providers lock -fs-mirror=... -platform=linux_amd64
  -platform=darwin_arm64` if those binaries change. Never reuse the v0.16 Tofu
  state. The runner uses suffix `manafishrov-stalwart-v1` and
  `upgradeOnInit: false`; leave the old backend Secrets intact.
- Confirm snapshot capacity, `mayastor-snapshot` readiness, and the recovery
  credentials outside this repo. Keep the encrypted captures and snapshot until
  rollback is no longer needed. The old paused VolSync backup is not a backup
  of this cutover.

[Recorded prepare answers](prepare-answers.md) explain each policy choice.
The Job seeds answers only when absent. `prepare --non-interactive` refuses
unanswered questions; review `prepare-report.txt` before accepting new ones.

## Cutover

1. Suspend the Flux `manafishrov` Kustomization and the parent reconciliation
   that manages the Terraform CR (`infrastructure-configs`), then suspend
   Terraform `manafishrov-stalwart`, all in `flux-system`. Ensure no runner is
   still applying. Keep reconciliation suspended while changing replicas and
   switching the runner/backend. Hold public HTTP/client access, Pocket ID SCIM
   writes and sending/delivery during the window; Postfix may queue new mail.
2. Create `snapshot.yaml`; wait for `stalwart-before-v1.status.readyToUse=true`
   and record its content/handle. This initial online snapshot is crash
   consistent. For the final recovery point, take another uniquely named
   snapshot after scaling down and before migration, and wait for readiness.
3. Before stopping v0.16.27, capture through authenticated native JMAP, using
   the existing authorized admin token in `STALWART_TOKEN` without echoing it:

   ```sh
   umask 077
   python3 apps/stalwart/migration/scim-fields.py capture /secure/scim-fields.json
   ```

   The helper paginates `x:Account/query` + `/get` (users and groups, including
   null `externalId`) and `x:Domain/query` + `/get` (`allowScimProvisioning`,
   including false). It refuses to overwrite an existing capture. Keep the
   capture outside Git; back it up encrypted. Also record all imported object
   IDs and role IDs; the DNS publisher is currently `jfi2hgdoabaa` (the DKIM
   handoff receipt). Confirm them after rehearsal/migration.
4. Scale StatefulSet `stalwart` to zero and wait for `stalwart-0` to disappear
   and its volume attachment to detach. Take the stopped snapshot from step 2.
   Do not run a migration Pod alongside the server. RWO scheduling may move
   the volume after detach; no node placeholder is required. Ensure Flux and
   other operators will not restore the replica count.
5. Create `config.yaml`, then `job.yaml` manually. The pinned OSS tool runs as
   UID/GID 2000 with fsGroup 2000, matching Stalwart, so no root `--owner` is
   needed. It validates prepare answers, runs `run --final --yes`, explicitly
   runs `verify`, then `status` and `report`. No error-bypass flags are used.
   Wait for Job completion and its Pod/volume release before starting Stalwart.
   A failed prepare never starts the copy. Review the persistent prepare report,
   final report and verification results securely; the tool's stdout alone is
   insufficient. Reports/state can contain sensitive settings.
6. Stage the filled v1 StatefulSet image and bootstrap ConfigMap together while
   replicas remain zero. Start one replica only after the Job has succeeded
   and released the PVC. The bootstrap remains `{"@type":"RocksDb","path":...}`;
   only its path changes to `data-v1/`. Check logs and `/healthz/ready` locally.
7. Restore SCIM fields with the patched v1 server, before re-enabling Pocket ID
   provisioning or applying Tofu:

   ```sh
   python3 apps/stalwart/migration/scim-fields.py restore /secure/scim-fields.json
   python3 apps/stalwart/migration/scim-fields.py verify /secure/scim-fields.json
   ```

   The helper checks ID/name/type/domain identity before each update, restores
   null/false as well as populated values, and reads each field back. Stop if
   IDs differ. The OSS tool does **not** preserve these fields: its v0.16
   reader knows them, but the v1 OSS mapping schema omits them and its v1
   writer gates them behind `enterprise`. The fork reintroduces them; the
   migration binary does not.
8. While Terraform and its parent remain suspended, stage both repositories'
   v1 changes. Verify the runner renders the provider mirror and fresh suffix,
   every import matches the migrated IDs, and the plan contains adoption and
   intended updates, with no duplicates/deletes or replacement secrets. The
   normal policy is auto approval: while the parent remains suspended, set the
   CR's `approvePlan` to an empty string before resuming Terraform against v1.
   Inspect the stored plan, approve its exact `status.plan.pending` value, and
   let the in-cluster apply finish. Return to `auto` only after verification.
   Never apply locally or point the old provider at v1. Check reload
   warnings as well as plan success; OIDC discovery must be reachable from the
   Stalwart Pod. Confirm WebUI 2.x assets load and a second plan is empty.
9. Before restoring access, verify HTTP `clientIpSource=xForwardedFor`,
   `forwardedHops=1`, and `abuseBanRate=null`. Test real client attribution,
   spoofed leftmost XFF, missing-header peer fallback, scanner/auth bans,
   non-admin isolation, Pocket ID admin login, SCIM IDs/provisioning flags,
   mailbox counts, shared identities, incoming and outbound mail/DKIM, private
   LMTP/SMTP and public submission/IMAPS/Sieve. Roll Bulwark to 1.21.0 and
   follow the OAuth notes in the parent README. Stalwart-issued OAuth tokens
   are not migrated; expect fresh sign-in. Keep the public mail URL unchanged.
10. Resume the parent Flux reconciliations only after the runner and server
    revisions are compatible. Re-enable provisioning and traffic, then release
    queued mail. Retain snapshots, the old data store/backend state and the
    migration state/report. Migration manifests must stay outside GitOps.

## Rollback

Before v1 accepts writes: suspend Terraform/Flux again, stop v1, release its
PVC, switch bootstrap back to `/var/lib/stalwart/data/` and the recorded patched
v0.16.27 image/digest, then start v0.16.27. Revert the runner/provider and backend
suffix together before allowing old Tofu reconciliation; never mix old state
with new schemas. The untouched `data/` is the rollback, not the currently
unfilled v1 manifest's predecessor v0.16.21 image.

After v1 accepts mail or account changes, the old store is stale. Hold delivery
and reconcile new mail/queues before rollback; never simply start both servers.
The tool's `rollback` copies v1 into a **new empty** v0.16 location, with its own
state and `--forward-state` pointing at this migration state. It must be
rehearsed separately and needs the same fork-only SCIM capture/restore. Never
point `rollback` at the preserved `data/`. A snapshot recovery likewise loses
writes after that snapshot unless they are separately reconciled.

Sources: [v1.0.6 migration README](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.6/README.md),
[prompt catalogue](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.6/mapping/prompts.toml),
[OSS field gates](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.6/vendor/v1/crates/registry/src/schema/structs.rs),
[conversion rules](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.6/mapping/v016_to_v1.toml).

Offline helper checks: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover
-s apps/stalwart/migration -p 'test_*.py'`. These use mocked JMAP responses;
they do not replace the PVC rehearsal or prove live provisioning.
