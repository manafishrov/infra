# AGENTS.md

## Purpose

Kubernetes infrastructure for Manafishrov. Apps are reconciled by FluxCD;
external resources (DNS, RustFS buckets, Pocket ID clients, Postgres roles)
are managed by OpenTofu
via tf-controller. Encrypted secrets live in the sibling repo
`../infra-secrets`.

This repo stays cluster-agnostic. Flux + tf-controller wiring lives in the
consumer cluster repo, not here.

## Structure

- `kustomization.yaml` — root, references each app + `public-redirects`
- `apps/<name>/` — per-app bundle (Namespace, NetworkPolicy, HTTPRoute,
  Services, StatefulSet/Deployment). App secrets live at
  `../infra-secrets/apps/<name>/`.
  - Apps: `n8n`, `nextcloud`, `pocket-id`, `roundcube`, `twenty`,
    `vaultwarden`
- `public-redirects/` — shared public namespace + redirect HTTPRoutes
- `tofu/<stack>/` — one OpenTofu root module per stack:
  - `rustfs` — firmware S3 bucket (public-read) and
    Twenty CRM S3 bucket (private), each with a matching IAM user/policy.
    Reads `rustfs_endpoint`, `rustfs_access_key`, `rustfs_secret_key`,
    `manafishrov_firmware_ci_secret_key`,
    `manafishrov_twenty_app_secret_key`. Writes
    `manafishrov_twenty_rustfs_access_key_id`,
    `manafishrov_twenty_rustfs_secret_access_key` into Secret
    `manafishrov-rustfs-outputs` (consumed by
    `apps/twenty/`).
  - `dns` (cloudflare) — records for `manafishrov.com`. Reads
    `CLOUDFLARE_API_TOKEN` from the runner env.
  - `pocket-id` — OIDC clients against the company pocket-id. Reads
    `manafishrov_pocketid_api_token`. Writes
    `manafishrov_vaultwarden_pocketid_client_id`,
    `manafishrov_vaultwarden_pocketid_client_secret`,
    `manafishrov_nextcloud_pocketid_client_id`,
    `manafishrov_nextcloud_pocketid_client_secret`,
    `manafishrov_n8n_pocketid_client_id`,
    `manafishrov_n8n_pocketid_client_secret`,
    `manafishrov_roundcube_pocketid_client_id`,
    `manafishrov_roundcube_pocketid_client_secret`,
    `manafishrov_twenty_pocketid_client_id`,
    `manafishrov_twenty_pocketid_client_secret` into Secret
    `manafishrov-pocket-id-outputs` (consumed by `apps/vaultwarden/`,
    `apps/nextcloud/`, `apps/n8n/`, `apps/roundcube/`, `apps/twenty/`).
  - `postgres` — application roles + databases on the
    shared cluster Postgres at `postgres.postgres.svc.cluster.local`.
    Reads `pg_admin_user`, `pg_admin_password`,
    `manafishrov_nextcloud_db_password`,
    `manafishrov_twenty_db_password`. Writes those password variables into
    `manafishrov-postgres-outputs` (consumed by `apps/nextcloud/`,
    `apps/twenty/`).
- `flake.nix` — dev shell

## Commands

Use the dev shell (`nix develop` or direnv).

```sh
kustomize build . | kubeconform -strict -ignore-missing-schemas \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'

tofu -chdir=tofu/<stack> fmt -check
tofu -chdir=tofu/<stack> init -backend=false
tofu -chdir=tofu/<stack> validate
```

Tofu is applied **in-cluster by tf-controller**, never locally. To add a
sensitive variable: declare in `tofu/<stack>/variables.tf`, add the value
to `../infra-secrets/apps/<app>/secrets.yaml`, then ask the consumer
operator to wire it into the matching `Terraform` CR.

## Rules

- Pushing to `main` is deploying. Don't push without being asked.
- **No secrets in this repo** — they live in `../infra-secrets`.
- Each app self-contained under `apps/<name>/`. Each tofu stack
  self-contained under `tofu/<stack>/` (no cross-stack refs — duplicate
  via a Secret).
- The `apps/pocket-id/` instance is the **company's own** pocket-id; do
  not share with personal infrastructure.
- Run the validate commands above before considering a change done.

## Commits

Conventional Commits, focused on **why**.

- Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `ci`, `revert`.
  `chore(deps)` reserved for Renovate.
- Scopes: `n8n`, `nextcloud`, `pocket-id`, `roundcube`, `twenty`,
  `vaultwarden`, `public-redirects`, `tofu/rustfs`, `tofu/dns`,
  `tofu/pocket-id`, `tofu/postgres`, `flake`, `ci`, or a new app name.
- Subject: imperative, lowercase, ≤72 chars, no period.

## Keep this file useful

If you add/rename an app or tofu stack, change validation commands, or
change Flux watch paths — update this file (and Renovate
`managerFilePatterns`) in the same commit.
