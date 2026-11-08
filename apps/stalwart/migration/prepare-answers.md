# Recorded prepare answers

The Job seeds `migration-v1/answers.toml` from `config.yaml` only when absent.
`prepare --non-interactive` validates it against the actual source and refuses
unanswered questions. Review `prepare-report.txt`; any new question needs an
explicit answer and another review, not automatic acceptance.

| Question | Answer and reason |
| --- | --- |
| Categories | All, including queue/tasks and spam models; final run copies final-only categories with the old server stopped. Empty enterprise categories do not create enterprise support. |
| Blob store | `copy`, if asked; keeps rollback isolated. RocksDB-resident blobs are always copied without this question. |
| Pocket ID directory `jdzlxs2sajaa` | Audience `stalwart`, audience validation on, opaque tokens via `userInfo`, display claim `name`; preserves the existing integration. ID-token claims, lenient issuer matching and invalid certificates stay disabled. |
| Tokens without Stalwart scopes | `full`; preserves existing Pocket ID WebUI administration and webmail. Tokens still receive only the account's native permissions. `interoperable` would remove the existing admin/settings access from these `openid email` tokens. This is an explicit compatibility choice, not the tool's narrower recommendation. |
| OAuth registration | `accept`; v1 requires registered clients and permits rate-limited public registration. Inventory old arbitrary client IDs during rehearsal. |
| OAuth lifetimes | `clamp`, only if below v1 minimums; 10 minutes for codes/access tokens and one day for refresh idle timeout. |
| HTTP forwarding | `xForwardedFor`, one hop, only if old `useXForwarded` is true. Today's false is converted to `peer` without a question. Tofu changes it to XFF before reopening HTTP traffic. |
| Migrated OAuth clients | `interoperable`; mail, contacts, calendars and files. Grant `full` only to an explicitly managed client that needs it. This is separate from external Pocket ID token policy. |
| Enterprise-only fields | `drop` with report review; the patched server and migration tool are OSS. Restore the fork's SCIM fields separately. Disabled SpamLlm has no v1 OSS resource. |
| New permissions | `grant` to roles with the matching old permissions; preserves functionality. Default roles/sign-in grant-management permissions are completed by the tool regardless. |
| Encryption at rest | Header protection `none`, if asked; preserves v0.16 behavior instead of changing encryption policy during migration. |
| Changed defaults | `pin`; preserve behavior while changing storage/schema. Tofu explicitly changes the HTTP policy afterward. |

AI models, SIG(0), Azure auth, clustered in-memory storage and counter-read
expressions are not configured here. If the actual source raises one of these
questions, prepare fails closed. Answers for absent optional questions are
harmless and may be omitted from the tool's rewritten answers file.

Source: [v1.0.6 prompt catalogue](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.6/mapping/prompts.toml).
