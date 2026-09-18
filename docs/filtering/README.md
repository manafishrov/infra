# Superseded score-bridge evidence

The header-score bridge was qualified but never deployed. Postfix with native
PROXY context replaces it, including native authentication and contact trust.
Do not install its header-rule overrides or enable filtering on old LMTP.

`qualification.json` and `validation.json` retain the historical results.
Commit `6349b97` contains the retired patches and their tests; those patches no
longer apply to the current configuration and their promotion scripts were
removed.

Current backend ordering and queue-safety gates are in
[`tofu/stalwart/ACTIVATION.md`](../../tofu/stalwart/ACTIVATION.md). Production
plans and applies belong to tf-controller, not a local Terraform invocation.
