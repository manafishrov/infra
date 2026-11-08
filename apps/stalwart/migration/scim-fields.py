#!/usr/bin/env python3
"""Capture, restore, or verify fork-only SCIM fields through native JMAP.

Covers Account.externalId, Domain.allowScimProvisioning and the scimAccess
permission, all of which the OSS migrator drops as Enterprise-only. Restore
also grants the Tofu account v1's per-action reload permissions, which the
migration does not derive from its v0.16 permissions.
"""
import argparse
import base64
import json
import os
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["capture", "restore", "verify"])
    parser.add_argument("file", type=Path)
    parser.add_argument("--url", default="https://mail.manafishrov.com")
    args = parser.parse_args()
    os.umask(0o077)
    # Only a superuser can grant scimAccess, so restore uses the temporary
    # recovery admin (user:password); capture and verify can use the API key.
    recovery = os.environ.get("STALWART_RECOVERY_ADMIN")
    if recovery:
        authorization = "Basic " + base64.b64encode(recovery.encode()).decode()
    else:
        authorization = "Bearer " + os.environ["STALWART_TOKEN"]

    def request(url, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = Request(url, data, {"Authorization": authorization,
                                 "Content-Type": "application/json"})
        with urlopen(req, timeout=60) as response:
            return json.load(response)

    session = request(args.url.rstrip("/") + "/.well-known/jmap")
    account = session["primaryAccounts"]["urn:stalwart:jmap"]
    # Keep every call on --url: the session's apiUrl names the public host,
    # which would send rehearsal writes to production.
    api = urljoin(args.url, urlsplit(session["apiUrl"]).path)

    def call(method, **params):
        response = request(api, {
            "using": ["urn:ietf:params:jmap:core", "urn:stalwart:jmap"],
            "methodCalls": [[method, {"accountId": account, **params}, "0"]],
        })["methodResponses"][0]
        if response[0] != method:
            raise RuntimeError(f"{method} failed: {response[0]}")
        result = response[1]
        for key in ("notFound", "notCreated", "notUpdated", "notDestroyed"):
            if result.get(key):
                raise RuntimeError(f"{method} returned {key}; stop and inspect securely")
        return result

    def grant(account_id, names):
        def enabled():
            permissions = call("x:Account/get", ids=[account_id],
                               properties=["permissions"])["list"][0]["permissions"]
            return permissions, (permissions or {}).get("enabledPermissions") or {}

        permissions, granted = enabled()
        missing = [name for name in names if not granted.get(name)]
        if args.action == "restore" and missing:
            if (permissions or {}).get("@type") != "Replace":
                raise RuntimeError(f"x:Account/{account_id}: unexpected permissions shape; stop")
            call("x:Account/set", update={account_id: {"permissions": {
                **permissions, "enabledPermissions": {**granted, **dict.fromkeys(missing, True)}}}})
            permissions, granted = enabled()
            missing = [name for name in names if not granted.get(name)]
        if missing:
            raise RuntimeError(f"x:Account/{account_id}: {', '.join(missing)} missing")

    # The provider reloads after applying settings, certificates, blocked IPs
    # and lookup stores; without these, applied changes stay inactive.
    tofu_actions = ["actionReloadSettings", "actionReloadTlsCertificates",
                    "actionReloadBlockedIps", "actionReloadLookupStores"]

    objects = {"x:Account": "externalId", "x:Domain": "allowScimProvisioning"}
    if args.action == "capture":
        saved = {"url": args.url, "objects": {}}
        for kind, field in objects.items():
            rows = []
            position = 0
            while True:
                page = call(kind + "/query", position=position, limit=100,
                            calculateTotal=True)
                ids = page["ids"]
                if ids:
                    props = ["id", "name", field]
                    if kind == "x:Account":
                        props += ["@type", "domainId", "permissions"]
                    batch = call(kind + "/get", ids=ids, properties=props)["list"]
                    if len(batch) != len(ids) or any(field not in row for row in batch):
                        raise RuntimeError(f"{kind}: SCIM field missing; check fork/permissions")
                    if kind == "x:Account":
                        for row in batch:
                            permissions = row.pop("permissions") or {}
                            # v1 keeps suspension state elsewhere; a suspended
                            # account could not be reactivated through SCIM.
                            if (permissions.get("disabledPermissions") or {}).get("authenticate"):
                                raise RuntimeError(f"{kind}/{row['id']}: suspended; reactivate or delete first")
                            enabled = permissions.get("enabledPermissions") or {}
                            row["scimAccess"] = bool(enabled.get("scimAccess"))
                    rows.extend(batch)
                position += len(ids)
                if position >= page["total"]:
                    break
                if not ids:
                    raise RuntimeError(f"{kind}: incomplete pagination")
            saved["objects"][kind] = rows
        # Never overwrite the pre-migration capture with post-migration values.
        with args.file.open("x") as out:
            json.dump(saved, out, indent=2)
            out.write("\n")
    else:
        saved = json.loads(args.file.read_text())
        if saved["url"] != args.url:
            raise RuntimeError("Export belongs to another endpoint")
        for kind, field in objects.items():
            for row in saved["objects"][kind]:
                props = ["id", "name", field]
                if kind == "x:Account":
                    props += ["@type", "domainId"]
                current = call(kind + "/get", ids=[row["id"]], properties=props)["list"][0]
                identity = ("name", "@type", "domainId") if kind == "x:Account" else ("name",)
                if any(current.get(key) != row.get(key) for key in identity):
                    raise RuntimeError(f"{kind}/{row['id']}: identity changed; stop")
                if args.action == "restore":
                    call(kind + "/set", update={row["id"]: {field: row[field]}})
                    current = call(kind + "/get", ids=[row["id"]], properties=props)["list"][0]
                if field not in current or current[field] != row[field]:
                    raise RuntimeError(f"{kind}/{row['id']}: SCIM value differs")
                if kind == "x:Account" and row["scimAccess"]:
                    grant(row["id"], ["scimAccess"])
                if kind == "x:Account" and row["name"] == "tofu":
                    grant(row["id"], tofu_actions)
    print(f"SCIM {args.action} completed")


if __name__ == "__main__":
    main()
