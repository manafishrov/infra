# Android external-IdP login candidate

This is a tested source patch, **not a device-qualified fix**. Nothing here
changes production or the distributed Android app. Native release 0.1.62 rejects
the Pocket ID token endpoint during both webmail handoff and QR pairing.

## Pinned sources and reproduction

- Upstream: <https://github.com/bulwarkmail/native>, release `0.1.62`.
- Source commit: `6c82130267263a43aac885a701b4ed4d144b6092`.
- Annotated tag object: `5561802c5da2d7ae807a72158133491f54301e7c`
  (this is not the source commit).
- The inspected upstream main commit,
  `5b8c4353d858c3d160ac5bc8f68235371f9afda7`, has the same `src/lib/oauth.ts`.
- Deployed webmail: `1.9.2`, source commit
  `2f1192bb3285dea2c8b8ece461d52967fe0e6706`.

The native validator accepts matching, ancestor, or descendant hostnames.
Pocket ID at `id.manafishrov.com` is a sibling of both
`mail.manafishrov.com` and `mail-admin.manafishrov.com`, so it fails that check.
Both `runWebmailHandoff` and `redeemPairingCode` use the validator. QR pairing
therefore cannot work around this failure.

Public HTTPS responses from the deployed services confirmed:

| Field | Value |
| --- | --- |
| Webmail `/api/config`: JMAP URL | `https://mail-admin.manafishrov.com` |
| Webmail `/api/config`: OAuth client | `stalwart` |
| Webmail `/api/config`: issuer | `https://id.manafishrov.com` |
| Webmail `/api/auth/oauth/metadata`: issuer | `https://id.manafishrov.com` |
| Webmail metadata and Pocket ID discovery: token endpoint | `https://id.manafishrov.com/api/oidc/token` |

The retained tests use fixtures for these public values, not live production
requests. They execute the entire real upstream `oauth.ts` module after Node
strips TypeScript types. Only its three platform dependencies are substituted:
Expo's browser session, `secureFetch`, and the random-state generator. The
actual callback parsing, state check, endpoint check, handoff, and pairing
call sites run unchanged except for the candidate patch.

### Run red, then green

Requires Git and Node.js 24 (tested with 24.15.0). Run from the company repository
root. The checkout is temporary and independent of the infrastructure repository.
No npm dependencies are needed for this regression test.

```sh
qualification="$PWD/apps/stalwart/qualification/android-auth"
checkout="$(mktemp -d /tmp/bulwark-native-0.1.62.XXXXXX)"
git clone --depth 1 --branch 0.1.62 \
  https://github.com/bulwarkmail/native.git "$checkout"
test "$(git -C "$checkout" rev-parse HEAD)" = \
  6c82130267263a43aac885a701b4ed4d144b6092

# Expected RED: exit 1, two genuine-external-IdP failures.
# Exit 2 means setup failed, not a successful reproduction.
if node "$qualification/handoff-test.cjs" --checkout "$checkout" --baseline; then
  echo 'ERROR: baseline unexpectedly passed' >&2
  exit 1
else
  result=$?
  test "$result" -eq 1 || exit "$result"
fi

git -C "$checkout" apply --check "$qualification/native-external-idp.patch"
git -C "$checkout" apply "$qualification/native-external-idp.patch"

# Expected GREEN: exit 0, 47 passed, 0 failed.
node "$qualification/handoff-test.cjs" --checkout "$checkout"
git -C "$checkout" diff --check
```

Alternatively, set `BULWARK_NATIVE_CHECKOUT` instead of passing `--checkout`.
The runner rejects a different HEAD commit. `--baseline` always reads the pinned
Git object, even after applying the patch; the default reads the working file.
Node may print an experimental warning for its TypeScript-stripping API.

The baseline gives `45 passed, 2 failed`, with these specific failures:

```text
FAIL handoff: genuine external IdP: Sign-in response token endpoint is not trusted
FAIL pairing: genuine external IdP: Pairing response token endpoint is not trusted
```

The candidate gives `47 passed, 0 failed`: both external-IdP flows, both existing
same-host flows, 42 external-IdP rejection cases, and the handoff state-mismatch
case. Negative cases include endpoint substitution, HTTP, altered query,
hostname-suffix spoofing, userinfo, client/JMAP/issuer mismatch, missing config,
disabled OAuth, unavailable discovery, HTTP errors, surfaced redirects,
unavailable final URLs, and malformed JSON. The test tokens and pairing code
are visibly synthetic.

The transport regression cases exercise missing final URLs and responses marked
as redirected, independently for config and metadata in both login flows. The
pre-review candidate failed all eight of these cases (`39 passed, 8 failed`);
the retained patch passes them. Successful fixtures explicitly report the
requested URL; they do not silently substitute an empty-URL `Response`.

## Security boundaries

The patch changes only native `src/lib/oauth.ts`. It retains the existing
same-host validator and adds a fail-closed path for external IdPs:

1. Fetch public configuration from the **user-selected webmail**, never from a
   callback-provided origin.
2. Require HTTPS without URL userinfo or fragments for the external token
   endpoint, JMAP URL, selected webmail, and configured issuer.
3. Match the callback's client ID and JMAP URL exactly to webmail configuration.
4. Fetch the webmail's existing server-resolved OAuth metadata. Match its issuer
   exactly to the configured issuer, and its token endpoint exactly to the
   callback's endpoint. No wildcard or parent-domain exception is added.
5. Reject failed discovery. Request redirect refusal and reject non-success
   responses, any missing or different final URL, and responses marked as
   redirected. Set an abort timer and the native wrapper's `timeoutMs` to 8,000
   ms per request. Discovery requests carry no access or refresh token.

The selected webmail and its administrator-managed config remain trust anchors.
Public metadata does not need a user session, but it must arrive over trusted
HTTPS. A compromised or deliberately selected malicious webmail is outside
this patch's protection. Existing ancestor/descendant hostname acceptance and
loopback behavior are unchanged, not independently qualified by this work.

Matching the OAuth client ID is **not JWT audience validation**. Stalwart still
validates tokens and native permissions; this patch does not replace or relax
issuer, audience, signature, or TLS verification. It does not alter the PKCE
flow, request more scopes, add accounts, bypass passkeys, or make the custom
callback scheme resistant to interception by another installed app.

The runner mocks the HTTP transport and browser, so it does not prove Android
certificate validation, redirect handling, timeout enforcement, refresh traffic,
or custom-scheme routing. Normal Android fetch must report the exact final URL
and must not follow redirects unnoticed; that behavior still needs real-device
qualification. A transport that cannot supply the required evidence fails
closed instead of gaining external-IdP trust.

**The native-client-certificate transport is unsupported for this external-IdP
path.** Its `secureFetch` branch ignores `init.redirect` and `init.signal`,
handles redirects itself, and constructs a new `Response` with an empty `.url`.
The retained patch therefore rejects its metadata responses, even when their
JSON is otherwise valid. `timeoutMs: 8000` reaches that branch's native request
timeout, but does not repair its missing destination evidence or qualify it.
There is no transport refactor in this candidate. Existing same-host behavior
is untouched; this work is not a general security audit.

The patch is scoped to this single-server webmail configuration; other
deployments need their own qualification.

## TypeScript and bundle checks

The following checks ran in a temporary checkout using the upstream lockfile:

| Check | Pinned baseline | Candidate |
| --- | --- | --- |
| `npm ci --ignore-scripts --no-audit --no-fund` | Passed | Same dependencies |
| `npm run typecheck` | Passed | Passed |
| `npm test` | 966 passed, 14 skipped | 966 passed, 14 skipped |
| Android-targeted Expo JavaScript/Hermes export | Not run | Passed, 3,992 modules |

Vitest reported 77 passed test files and one skipped file. Skipped tests are not
qualification evidence. Reproduce the candidate checks after the green run:

```sh
(
  cd "$checkout"
  npm ci --ignore-scripts --no-audit --no-fund
  npm run typecheck
  npm test
  output="$(mktemp -d /tmp/bulwark-android-export.XXXXXX)"
  CI=1 EXPO_OFFLINE=1 EXPO_NO_TELEMETRY=1 \
    ./node_modules/.bin/expo export --platform android --output-dir "$output"
)
```

This produces a JavaScript/Hermes bundle, **not an APK or AAB**. No Android SDK
license was accepted, signing key accessed, app installed, or deployment made.
The upstream source is AGPL-3.0-only; retain its notices and account for its
source-distribution requirements when choosing a distribution path.

## Exact remaining blockers

1. **Release signing and distribution choice.** Choose whether to wait for an
   upstream release or maintain/distribute a patched build. A patched release
   needs a signing-key owner, application identity/update-path decision, and
   distribution channel. This worker has not made that choice or signed a
   release. There is no fixed distributed app from this work.
2. **Genuine connected device and passkey login.** Open Browser Use returned no
   installed/connected profiles, and `adb`, `emulator`, `gradle`, and `java` were
   absent from PATH during investigation. Connect the intended Android device
   and browser; the real user must complete Pocket ID authentication with their
   passkey. Do not substitute an admin token, session injection, or a new account.

After those blockers are resolved, use the corresponding real users to check:

- Native handoff, authenticated JMAP access, and token refresh against Pocket ID.
- Personal/shared mailbox visibility and folder lists without opening production
  message bodies.
- Sending from shared identities using an explicitly agreed test message and
  recipient.
- Non-administrator isolation, sign-out, and a fresh genuine login.
- QR pairing with a fresh user-authorized pairing code, if pairing is to be
  supported; a successful browser login alone does not qualify it.

These real-user checks remain unperformed. Public endpoints, redirects, source
unit tests, and a successful bundle export do not replace them.
