# Infra

Kubernetes infrastructure for Manafishrov managed via
[OpenTofu](https://opentofu.org) and [FluxCD](https://fluxcd.io).

## Development

```sh
nix develop

kustomize build . | kubeconform -strict -ignore-missing-schemas \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'

# Per stack: storage, dns, identity
tofu -chdir=tofu/<stack> fmt -check
tofu -chdir=tofu/<stack> init -backend=false
tofu -chdir=tofu/<stack> validate
```

See [`AGENTS.md`](AGENTS.md) for the full Flux contract, state migration
runbook, and operational rules.

## License

This project is licensed under the GNU Affero General Public License v3.0 or
later - see the [LICENSE](LICENSE) file for details.
