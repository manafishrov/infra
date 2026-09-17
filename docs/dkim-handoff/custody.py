#!/usr/bin/env python3
"""One-time, explicitly approved File -> Text import of Manafish's two DKIM keys.

No secret discovery: the operator supplies PEM strings on stdin and an API token
in STALWART_TOKEN. Default mode checks only. See README.md before using --apply.
"""

import argparse
import base64
import hashlib
import json
import os
import resource
import ssl
import subprocess
import sys
import urllib.request
from urllib.parse import urlsplit

DOMAIN_ID = "c"
KEYS = {
    "rsa": ("jdzlxs2ualqa", "stalwart-rsa", "Dkim1RsaSha256"),
    "ed25519": ("jdzlxs2uamqa", "stalwart-ed25519", "Dkim1Ed25519Sha256"),
}
PROPERTIES = [
    "id", "@type", "domainId", "selector", "stage", "nextTransitionAt",
    "publicKey", "canonicalization", "headers", "auid", "expire", "report",
    "thirdParty", "thirdPartyHash", "memberTenantId",
]
MAX_INPUT = 32768


class HandoffError(Exception):
    """Only fixed, non-secret messages may cross the CLI boundary."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HandoffError("Management redirects are forbidden")


class NativeAPI:
    def __init__(self, endpoint, token, ca_file=None):
        url = urlsplit(endpoint)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.query or url.fragment or url.path not in ("", "/")):
            raise HandoffError("Use the private management HTTPS origin, without a path")
        if not token or "\n" in token or "\r" in token:
            raise HandoffError("STALWART_TOKEN is required")
        self.endpoint = endpoint.rstrip("/") + "/jmap"
        self.token = token
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)),
        )

    def call(self, method, arguments):
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps({
                "using": ["urn:ietf:params:jmap:core", "urn:stalwart:jmap"],
                "methodCalls": [[method, arguments, "dkim-custody"]],
            }).encode(),
            headers={"Authorization": "Bearer " + self.token,
                     "Content-Type": "application/json"},
            method="POST",
        )
        # Do not print HTTP errors or server bodies: they may echo submitted keys.
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(131073)
            if len(raw) > 131072:
                raise HandoffError("Oversized management response")
            responses = json.loads(raw)["methodResponses"]
            if len(responses) != 1:
                raise HandoffError("Unexpected management response")
            name, result, tag = responses[0]
            if name != method or tag != "dkim-custody" or not isinstance(result, dict):
                raise HandoffError("Management method failed")
            return result
        except HandoffError:
            raise
        except Exception:
            raise HandoffError("Management request failed; response suppressed") from None


def public_key(pem, algorithm):
    if not isinstance(pem, str) or not pem or len(pem) > MAX_INPUT:
        raise HandoffError("Supply both existing PEM strings")
    # stdin only: no key arguments, files, child-process logs or inherited token.
    try:
        result = subprocess.run(
            ["openssl", "pkey", "-pubout", "-outform", "DER", "-passin", "pass:"],
            input=pem.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10, check=False, env={"PATH": os.environ.get("PATH", "")},
        )
        if result.returncode:
            raise HandoffError("Private key parsing failed; diagnostic suppressed")
        der = result.stdout
        if algorithm == "ed25519":
            prefix = bytes.fromhex("302a300506032b6570032100")
            if len(der) != len(prefix) + 32 or not der.startswith(prefix):
                raise HandoffError("Expected an Ed25519 private key")
            der = der[len(prefix):]
        elif algorithm != "rsa":
            raise HandoffError("Unexpected signing algorithm")
        # RSA output is SubjectPublicKeyInfo, matching Stalwart's publicKey.
        return base64.b64encode(der).decode("ascii")
    except HandoffError:
        raise
    except Exception:
        raise HandoffError("Key validation failed; diagnostic suppressed") from None


def read_signatures(api, include_private=False):
    ids = [entry[0] for entry in KEYS.values()]
    properties = PROPERTIES + (["privateKey"] if include_private else [])
    result = api.call("x:DkimSignature/get", {"ids": ids, "properties": properties})
    rows = result.get("list", [])
    if result.get("notFound") or len(rows) != len(ids):
        raise HandoffError("Expected both existing signatures")
    found = {row["id"]: row for row in rows}
    if set(found) != set(ids):
        raise HandoffError("Unexpected signature IDs")
    return found


def migrate(api, keys, apply=False):
    if not isinstance(keys, dict) or set(keys) != set(KEYS):
        raise HandoffError("stdin must contain only rsa and ed25519 PEM strings")
    domain = api.call("x:Domain/get", {
        "ids": [DOMAIN_ID], "properties": ["id", "name", "dkimManagement"],
    })
    rows = domain.get("list", [])
    if (domain.get("notFound") or len(rows) != 1 or rows[0].get("id") != DOMAIN_ID
            or rows[0].get("name") != "manafishrov.com"
            or rows[0].get("dkimManagement", {}).get("@type") != "Manual"):
        raise HandoffError("Manafish domain must exist with Manual DKIM management")
    before = read_signatures(api)
    updates = {}
    receipt = []
    for algorithm, (key_id, selector, kind) in KEYS.items():
        row = before[key_id]
        if (row.get("@type") != kind or row.get("domainId") != DOMAIN_ID
                or row.get("selector") != selector or row.get("stage") != "active"
                or row.get("nextTransitionAt") is not None):
            raise HandoffError("Signature metadata differs from the approved handoff")
        derived = public_key(keys[algorithm], algorithm)
        if derived != row.get("publicKey"):
            raise HandoffError("Supplied private key does not match the current native public key")
        # Replace the entire tagged union; never leave a stale filePath behind.
        updates[key_id] = {"privateKey": {"@type": "Text", "secret": keys[algorithm]}}
        receipt.append({"id": key_id, "selector": selector,
                        "publicKeySha256": hashlib.sha256(base64.b64decode(derived)).hexdigest()})
    if apply:
        result = api.call("x:DkimSignature/set", {"update": updates})
        if result.get("notUpdated") or set(result.get("updated", {})) != set(updates):
            raise HandoffError("Import may be partially applied; keep mounts and recheck both keys")
        after = read_signatures(api, include_private=True)
        for key_id in updates:
            private = after[key_id].pop("privateKey", None)
            # Native SecretTextValue.into_value always masks secret as "****".
            # Verify custody form, not plaintext; publicKey below proves identity.
            if (not isinstance(private, dict) or private.get("@type") != "Text"
                    or set(private) - {"@type", "secret"}):
                raise HandoffError("Native Text custody was not confirmed; retain original mounts")
        if after != before:
            raise HandoffError("Post-import metadata changed; stop and retain original mounts")
    return {"mode": "imported" if apply else "checked", "signatures": receipt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--ca-file")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--ownership-released", action="store_true")
    parser.add_argument("--phase0-verified", action="store_true")
    args = parser.parse_args()
    if args.apply and not (args.ownership_released and args.phase0_verified):
        parser.error("--apply requires --ownership-released and --phase0-verified")
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        api = NativeAPI(args.endpoint, os.environ.get("STALWART_TOKEN", ""), args.ca_file)
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise HandoffError("Oversized input")
        receipt = migrate(api, json.loads(raw), args.apply)
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except Exception:
        # No exception text or traceback: JSON/parser/server errors can contain PEMs.
        print("DKIM handoff failed. A write may be partially applied; retain mounts and recheck.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
