# Infra

Kubernetes infrastructure for Manafishrov managed via
[OpenTofu](https://opentofu.org) and [FluxCD](https://fluxcd.io).

## Development

```sh
nix develop

kustomize build . | kubeconform -strict -ignore-missing-schemas \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'

# Per stack: rustfs, dns, pocket-id, postgres, stalwart
tofu -chdir=tofu/<stack> fmt -check
tofu -chdir=tofu/<stack> init -backend=false
tofu -chdir=tofu/<stack> validate
```

See [`AGENTS.md`](AGENTS.md) for the repository structure, deployment model,
and operational rules.

## Stalwart management

`tofu/stalwart` adopts and manages the production server configuration through
Stalwart's JMAP management API. SCIM continues to own mailbox users, shared
mailbox groups, and their memberships; they are deliberately absent from the
OpenTofu state.

The controller authenticates with an API-key-only system principal whose
permissions are restricted to Stalwart's `sys*` management surface. Human
administration is granted only for OIDC sessions carrying the exact Pocket ID
`email-admin` group; no native Admin role is persisted. Pocket ID uses a separate,
mailbox-only client as its SCIM synchronization boundary so the authorization
group is never provisioned as a shared mailbox. No recovery or
password-bearing administrator is retained. A completely fresh database
therefore requires a one-time recovery bootstrap to create that principal and
API key; remove the temporary recovery credential immediately after OpenTofu
has adopted the server.

`tahacodes/stalwart` is pinned to `0.2.3`. Because it is not published in the
OpenTofu registry, the runner installs the upstream release into a filesystem
mirror after verifying the architecture-specific SHA-256 digest.

## License

This project is licensed under the GNU Affero General Public License v3.0 or
later - see the [LICENSE](LICENSE) file for details.
