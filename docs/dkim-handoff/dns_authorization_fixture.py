#!/usr/bin/env python3
"""Qualify native DNS scheduling authority in a disposable normal-mode server.

Run with --binary /path/to/approved/stalwart and
--fixture-directory /path/to/infra/packages/stalwart-oss.
Requires Linux, unshare, iproute2, openssl, and the trusted integration/mail helpers.
The launcher always creates fresh user/network namespaces with only loopback.
Recovery mode provisions the disposable database ONLY; every authorization
assertion runs after a normal-mode restart with a restricted fixture account.

A generated DKIM key ensures publication has real work to attempt. The fake
Cloudflare provider must fail inside isolation: this proves scheduling and
provider dispatch, NOT successful publication or production API-key inheritance.
No production configuration, credentials, or writable host resolver is used.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True

APPROVED_SHA256 = "02030a8334e3bc62bae1fa4a9139f498df0a7e105bd97ec5beacfdfa1be8b614"


def report(label, value):
    print(label + ": " + json.dumps(value, sort_keys=True), flush=True)


def task_rows(client):
    ids = client.jmap("x:Task/query", {})["ids"]
    return client.jmap("x:Task/get", {"ids": ids})["list"] if ids else []


def task_ids(rows):
    return {row["id"] for row in rows}


def run(args, mail, integration):
    require = integration.require
    integration.check_namespace(args.parent_netns, args.parent_userns)
    mail.isolated()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with args.binary.open("rb") as source:
        require(hashlib.file_digest(source, "sha256").hexdigest() == APPROVED_SHA256,
                "Refusing binary: approved SHA-256 required")
    report("isolation", {
        "net": integration.namespace_id("net"),
        "user": integration.namespace_id("user"),
        "interfaces": ["lo"],
        "sha256": APPROVED_SHA256,
    })
    with tempfile.TemporaryDirectory(prefix="dkim-auto-normal-") as directory:
        client = integration.Client(mail.port(), integration.Redactor())
        server = integration.Server(args.binary, Path(directory), client)
        try:
            # Provision only. No authorization conclusion uses recovery mode.
            server.start()
            domain_id = mail.create(client, "Domain", {
                "name": "fixture.test",
                "certificateManagement": {"@type": "Manual"},
                "dkimManagement": {"@type": "Manual"},
                "dnsManagement": {"@type": "Manual"},
            })
            dns_id = mail.create(client, "DnsServer", {
                "@type": "Cloudflare",
                "description": "isolated fake provider",
                "secret": {"@type": "Value", "secret": "fakefixtureaccount"},
                "timeout": 1000,
            })
            pem = subprocess.run(
                ["openssl", "genpkey", "-algorithm", "ED25519"],
                capture_output=True, check=True, timeout=20,
            ).stdout.decode()
            client.redactor.add(pem)
            mail.create(client, "DkimSignature", {
                "@type": "Dkim1Ed25519Sha256",
                "domainId": domain_id,
                "selector": "fixture-ed25519",
                "stage": "active",
                "nextTransitionAt": None,
                "privateKey": {"@type": "Text", "secret": pem},
            })
            permissions = dict.fromkeys((
                "authenticate", "sysDomainGet", "sysDomainUpdate",
                "sysTaskGet", "sysTaskQuery", "sysTaskCreate",
            ), True)
            account_id = mail.create(client, "Account", {
                "@type": "User",
                "name": "restricted",
                "domainId": domain_id,
                "roles": {"@type": "User"},
                "encryptionAtRest": {"@type": "Disabled"},
                "credentials": {"0": {"@type": "Password", "secret": server.password}},
                "permissions": {
                    "@type": "Merge",
                    "enabledPermissions": permissions,
                    "disabledPermissions": {"taskDnsManagement": True},
                },
            })
            account = client.jmap("x:Account/get", {"ids": [account_id]})["list"][0]
            report("provisioned_permissions", account["permissions"])
            port = client.origin.rsplit(":", 1)[1]
            mail.create(client, "NetworkListener", {
                "name": "fixture-http",
                "protocol": "http",
                "bind": {"127.0.0.1:" + port: True},
                "useTls": False,
            })
            mail.reload(client)
            # The helper calls this auth slot 'recovery'; replace its credential
            # with ordinary account Basic auth before restarting in normal mode.
            credential = account["emailAddress"] + ":" + server.password
            client.recovery = client.redactor.add(
                "Basic " + base64.b64encode(credential.encode()).decode())
            mail.start_mail(server)
            environment = Path(f"/proc/{server.process.pid}/environ").read_bytes()
            require(b"STALWART_RECOVERY" not in environment, "Recovery environment leaked")
            report("normal_mode", {
                "pid": server.process.pid,
                "no_recovery_environment": True,
            })

            before = client.jmap("x:Domain/get", {"ids": [domain_id]})["list"][0]
            initial = task_rows(client)
            report("initial_tasks", initial)
            explicit = client.jmap("x:Task/set", {"create": {"probe": {
                "@type": "DnsManagement",
                "domainId": domain_id,
                "updateRecords": {"dkim": True},
                "onSuccessRenewCertificate": False,
            }}}, allow_failure=True)
            report("explicit_task_denial", explicit)
            require(explicit[0] == "x:Task/set", "Expected per-object task denial")
            denial = explicit[1].get("notCreated", {}).get("probe", {})
            require(denial.get("type") == "forbidden" and denial.get("description") ==
                    "Insufficient permissions to create task of type DnsManagement",
                    "Expected task-specific permission denial, not a generic create denial")
            require(task_ids(task_rows(client)) == task_ids(initial),
                    "Denied create changed task IDs")

            automatic = {
                "@type": "Automatic",
                "dnsServerId": dns_id,
                "publishRecords": {"dkim": True},
            }
            update = {"update": {domain_id: {"dnsManagement": automatic}}}
            report("domain_update", client.jmap("x:Domain/set", update))
            after = client.jmap("x:Domain/get", {"ids": [domain_id]})["list"][0]
            require(before["dnsManagement"] == {"@type": "Manual"},
                    "Expected Manual DNS baseline")
            require(all(after["dnsManagement"].get(key) == value
                        for key, value in automatic.items()), "Wrong DNS management state")
            for key in ("dkimManagement", "certificateManagement"):
                require(before[key] == after[key] == {"@type": "Manual"}, key + " changed")
            rows = task_rows(client)
            report("scheduled_tasks", rows)
            added = [row for row in rows if row["id"] not in task_ids(initial)]
            require(len(added) == 1, "Expected exactly one new task")
            task = added[0]
            require(task["@type"] == "DnsManagement" and task["domainId"] == domain_id
                    and task["updateRecords"] == {"dkim": True}
                    and task["onSuccessRenewCertificate"] is False,
                    "Wrong scheduled task")
            report("management_after", {key: after[key] for key in (
                "dnsManagement", "dkimManagement", "certificateManagement")})

            # A provider failure can arrive before the first task read. Poll for
            # that terminal result rather than claiming Pending means publication.
            deadline = time.monotonic() + 20
            while True:
                final_rows = task_rows(client)
                final_task = next((row for row in final_rows if row["id"] == task["id"]), None)
                require(final_task is not None, "DNS task disappeared without failure evidence")
                if final_task["status"]["@type"] == "Failed":
                    break
                require(time.monotonic() < deadline, "Timed out waiting for isolated provider failure")
                time.sleep(0.2)
            report("isolated_provider_failure", final_task)
            reason = final_task["status"].get("failureReason", "")
            require("api.cloudflare.com" in reason and "Failed to send request" in reason,
                    "Expected isolated Cloudflare transport failure")
            client.jmap("x:Domain/set", update)
            require(task_ids(task_rows(client)) == task_ids(final_rows),
                    "Unchanged Automatic update scheduled another task")
            report("idempotent_automatic_update", "no additional task")
            report("PASS", "Normal-mode explicit task denied; domain update schedules exactly "
                   "DKIM-only task; manual DKIM/certificate unchanged. Provider failed in "
                   "isolation; no publication success claim.")
        finally:
            server.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--fixture-directory", type=Path, required=True)
    parser.add_argument("--namespace-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--parent-netns", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--parent-userns", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.binary = args.binary.resolve(strict=True)
    args.fixture_directory = args.fixture_directory.resolve(strict=True)
    # These are explicitly supplied, trusted helpers, not production adapters.
    sys.path.insert(0, str(args.fixture_directory))
    import integration
    import mail

    if args.namespace_child:
        integration.require(args.parent_netns is not None and args.parent_userns is not None,
                            "Missing parent namespace identities")
        run(args, mail, integration)
        return 0

    # Do not forward credentials, Python injection settings, or Stalwart config.
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return subprocess.call([
        "unshare", "-Urn", sys.executable, "-B", str(Path(__file__).resolve()),
        "--binary", str(args.binary), "--fixture-directory", str(args.fixture_directory),
        "--namespace-child",
        "--parent-netns", str(integration.namespace_id("net")),
        "--parent-userns", str(integration.namespace_id("user")),
    ], env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
