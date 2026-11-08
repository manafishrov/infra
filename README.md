# Manafish Infra

Kubernetes and OpenTofu infrastructure for Manafish, deployed with
[FluxCD](https://fluxcd.io). Secrets live in the private `infra-secrets`
repository.

## Development

```sh
nix develop

kustomize build . | kubeconform -strict -ignore-missing-schemas \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'

tofu -chdir=tofu/<stack> fmt -check
tofu -chdir=tofu/<stack> init -backend=false
tofu -chdir=tofu/<stack> validate
```

## License

[AGPL-3.0-or-later](LICENSE)
