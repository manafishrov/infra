# AGENTS.md

## Purpose

Kubernetes infrastructure for Manafishrov. Apps are reconciled by FluxCD from
this repo; cluster bootstrap and external resources are managed by OpenTofu.
Encrypted secrets live in the sibling repo `../infra-secrets` (separate
GitRepository in flux; see that repo's `AGENTS.md`).

## Stack

- Kubernetes + Kustomize
- FluxCD (GitOps; pushing to `main` deploys)
- OpenTofu
- Nix flake for the dev shell

## Structure

- `kustomization.yaml` — root, references each app
- `apps/<name>/` — per-app Kustomize bundle (Namespace, NetworkPolicy,
  HTTPRoute, Services, StatefulSet/Deployment). Secret manifests live in
  `../infra-secrets/gitops/<name>/` and are applied by a separate flux
  Kustomization.
  - Current apps: `pocket-id`, `vaultwarden`
- `tofu/` — OpenTofu root module (`main.tf`, `variables.tf`, `outputs.tf`)
- `flake.nix` — dev shell (`kubectl`, `kustomize`, `fluxcd`, `opentofu`,
  `gh`, `jq`, `yq-go`, `age`, `sops`)

## Commands

Use the dev shell (`nix develop` or direnv). Then:

### Validate without applying

```sh
kustomize build . | kubeconform -strict -ignore-missing-schemas \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'
```

For a single app: `kustomize build apps/<name> | kubeconform …`.

### OpenTofu

```sh
tofu -chdir=tofu fmt -check
tofu -chdir=tofu init -backend=false
tofu -chdir=tofu validate
```

Auto-format: `tofu -chdir=tofu fmt`.

Tofu is applied **in-cluster by tf-controller**, not locally. Variable
values come from Kubernetes Secrets in `flux-system` via `varsFrom` on the
`manafishrov-infra` Terraform CR (defined in the personal espresso flux
config). Adding a new sensitive variable requires:

1. Declare it in `tofu/variables.tf`.
2. Add the value to the appropriate Secret in
   `../infra-secrets/gitops/<app>/secrets.yaml` (or create a new
   `<app>-terraform-env` Secret).
3. Reference it in the personal `manafishrov-infra` Terraform CR's
   `varsFrom`.

## Rules

- Pushing to `main` is deploying — only push when the change is meant to
  roll out. Don't push without being asked.
- **No secrets — encrypted or plaintext — in this repo.** All secret
  manifests live in `../infra-secrets`. If you need to add one, add it
  there.
- Each app stays self-contained under `apps/<name>/` and is wired into the
  root `kustomization.yaml`. Its secrets (if any) live at
  `../infra-secrets/gitops/<name>/`.
- Match existing manifest style and label/namespace conventions.
- Run the validate commands above before considering a change done.

## Releases

There are no versioned releases. Pushing to `main` is the release — FluxCD
reconciles the cluster from this repo and tf-controller reconciles the
`tofu/` module from the same source. Don't push without being asked.

## Commits

Conventional Commits, focused on **why**.

```
<type>(<scope>): <subject>

[body explaining why, ~72 char wrap]
```

- Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `ci`, `revert`.
  `chore(deps)` reserved for Renovate.
- Scopes: `pocket-id`, `vaultwarden`, `tofu`, `flux`, `flake`, `ci`,
  or a new app name.
- Subject: imperative, lowercase, ≤72 chars, no period.
- Body when the why isn't obvious (especially for cluster-affecting
  changes).

## Keep this file useful

If you add an app under `apps/`, change the tofu layout, alter validation
commands, or change how Flux watches paths — update this file (and the
matching Renovate `managerFilePatterns`) in the same commit.
