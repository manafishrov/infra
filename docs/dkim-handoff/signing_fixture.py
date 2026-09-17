#!/usr/bin/env python3
"""Disposable normal-mode signing proof; no production endpoints or credentials.

Run in a fresh user/network namespace with only loopback, e.g.:
  unshare --user --map-root-user --net sh -c 'ip link set lo up; exec python3 -B \
    docs/dkim-handoff/signing_fixture.py --binary /path/to/approved/stalwart \
    --fixture-directory /path/to/personal/infra/packages/stalwart-oss'

Requires the existing mail.py/integration.py helpers, openssl, ip and named.
Two approved native instances exchange fixture mail over TLS LMTP. A private,
non-recursive DNS zone exposes only generated public keys. Native receiver
Authentication-Results verifies EACH signature, including independent corrupted
signature controls. This is not a Python reimplementation of DKIM verification.
"""

import argparse
from contextlib import contextmanager
from email.parser import BytesParser
from email.policy import default as email_policy
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
import custody

APPROVED_SHA256 = "02030a8334e3bc62bae1fa4a9139f498df0a7e105bd97ec5beacfdfa1be8b614"
DOMAIN = "manafishrov.com"
RELAY = "10.200.0.2"
RECEIVER = "receiver.fixture.test"


class FixtureError(RuntimeError):
    """Public fixture assertion, safe to report without API bodies or logs."""


def require(ok, reason):
    if not ok:
        raise FixtureError(reason)


@contextmanager
def local_dns(root, public_keys):
    """Authoritative-only fixture DNS; no forwarding and no host resolver edits."""
    zone = "$TTL 60\n@ IN SOA ns hostmaster (1 60 60 60 60)\n@ IN NS ns\nns IN A 127.0.0.1\n"
    for algorithm, public in public_keys.items():
        selector = custody.KEYS[algorithm][1]
        text = f"v=DKIM1; k={algorithm}; h=sha256; p={public}"
        zone += f'{selector}._domainkey IN TXT (' + " ".join(
            '"' + text[i:i + 200] + '"' for i in range(0, len(text), 200)) + ")\n"
    (root / "zone").write_text(zone)
    config = root / "named.conf"
    config.write_text(
        f'options {{ directory "{root}"; listen-on port 15353 {{ 127.0.0.1; }}; '
        'listen-on-v6 { none; }; recursion no; dnssec-validation no; '
        f'pid-file "{root}/named.pid"; session-keyfile "{root}/session.key"; }}; '
        f'controls {{ }}; zone "{DOMAIN}" {{ type primary; file "{root}/zone"; }};\n')
    with (root / "named.log").open("w") as log:
        process = subprocess.Popen(["named", "-g", "-n", "1", "-c", str(config)],
                                   stdout=log, stderr=subprocess.STDOUT,
                                   env={"PATH": os.environ["PATH"], "HOME": str(root)})
        try:
            time.sleep(0.5)
            require(process.poll() is None, "Fixture DNS failed to start")
            yield
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def tags(value):
    return {key.strip(): "".join(value.split()) for item in str(value).split(";")
            if "=" in item for key, value in [item.split("=", 1)]}


def verify(raw, failed=None):
    message = BytesParser(policy=email_policy).parsebytes(raw)
    signatures = [tags(value) for value in message.get_all("DKIM-Signature", [])]
    expected = {entry[1] for entry in custody.KEYS.values()}
    require(len(signatures) == 2 and {s.get("s") for s in signatures} == expected,
            "Expected exactly the two original selectors on outgoing mail")
    for signature in signatures:
        algorithm = "ed25519" if signature["s"] == "stalwart-ed25519" else "rsa"
        require(signature.get("d") == DOMAIN and signature.get("a") == algorithm + "-sha256",
                "Wrong signing domain or algorithm")
    # Only the NEW receiver-prepended result is evidence. Replayed originals may
    # contain older positive results; never search those for a convenient pass.
    results = message.get_all("Authentication-Results", [])
    require(results and str(results[0]).split(";", 1)[0].strip() == RECEIVER,
            "Missing fresh receiver Authentication-Results")
    verdicts = {}
    for clause in str(results[0]).split(";")[1:]:
        result = re.match(r"\s*dkim=(\w+)", clause)
        selector = re.search(r"\bheader\.s=([^\s;]+)", clause)
        if result and selector:
            require(selector[1] not in verdicts, "Duplicate verification result")
            verdicts[selector[1]] = result[1]
    require(set(verdicts) == expected, "Receiver did not verify both signatures")
    for selector, result in verdicts.items():
        require(result == ("fail" if selector == failed else "pass"),
                "Unexpected native DKIM result for " + selector + ": " + result)


def corrupt(raw, selector):
    headers, body = raw.split(b"\r\n\r\n", 1)
    fields = re.split(rb"\r\n(?![ \t])", headers)
    changed = 0
    for index, field in enumerate(fields):
        name, value = field.split(b":", 1)
        if name.lower() == b"dkim-signature" and tags(value.decode())["s"] == selector:
            fields[index], count = re.subn(
                rb"(\bb=[ \t\r\n]*)([A-Za-z0-9+/])",
                lambda m: m[1] + (b"B" if m[2] == b"A" else b"A"), field, count=1)
            changed += count
    require(changed == 1, "Could not corrupt exactly one signature")
    return b"\r\n".join(fields) + b"\r\n\r\n" + body


def capture(mail, receiver, send, user="alice"):
    """Retrieve exactly one newly delivered message, including deliberate replays."""
    def ids(connection):
        require(connection.select("INBOX")[0] == "OK", "Cannot select fixture inbox")
        status, rows = connection.search(None, "ALL")
        require(status == "OK", "Cannot enumerate fixture inbox")
        return set(rows[0].split())
    with mail.mailbox(receiver, user=user) as connection:
        before = ids(connection)
    send()
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        with mail.mailbox(receiver, user=user) as connection:
            new = ids(connection) - before
            if new:
                require(len(new) == 1, "Unexpected duplicate fixture delivery")
                status, data = connection.fetch(new.pop(), "(RFC822)")
                require(status == "OK", "Cannot fetch fixture delivery")
                return next(row[1] for row in data if isinstance(row, tuple))
        time.sleep(0.2)
    raise FixtureError("Native fixture delivery timed out")


def run(binary, fixture_directory):
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    links = json.loads(subprocess.check_output(["ip", "-j", "link", "show"]))
    require(len(links) == 1 and links[0]["ifname"] == "lo", "Require loopback-only netns")
    with binary.open("rb") as source:
        require(hashlib.file_digest(source, "sha256").hexdigest() == APPROVED_SHA256,
                "Refusing binary: approved deployment SHA-256 required")
    require(subprocess.check_output([str(binary), "--version"], text=True).strip() == "0.16.21",
            "Wrong native version")
    # Explicit, trusted local helper directory; never import edge*.py or mutate it.
    sys.path.insert(0, str(fixture_directory))
    import mail
    from integration import Client, Redactor, Server
    mail.isolated()
    subprocess.run(["ip", "address", "add", RELAY + "/32", "dev", "lo"], check=True)
    with tempfile.TemporaryDirectory(prefix="dkim-signing-") as directory:
        root = Path(directory)
        servers = []
        try:
            fixtures = []
            for name in ("sender", "receiver"):
                location = root / name
                location.mkdir()
                client = Client(mail.port(), Redactor())
                server = Server(binary, location, client)
                servers.append(server)
                server.start()
                fixture = mail.configure_backend(server, client, domain=DOMAIN,
                                                 lmtp_address=RELAY if name == "receiver" else None)
                account = client.jmap("x:Account/get", {"ids": [fixture["admin_id"]]})["list"][0]
                permissions = account["permissions"]
                for permission in ("sysDkimSignatureUpdate", "sysSenderAuthUpdate",
                                   "sysDnsResolverUpdate", "sysSystemSettingsUpdate", "sysMtaStageDataUpdate"):
                    permissions["enabledPermissions"][permission] = True
                client.jmap("x:Account/set", {"update": {fixture["admin_id"]: {"permissions": permissions}}})
                fixtures.append(fixture)
            sender, receiver = fixtures
            sc, rc = sender["client"], receiver["client"]
            api = type("API", (), {"call": staticmethod(sc.jmap)})()
            custody.DOMAIN_ID = sender["domain_id"]
            keys, files, targets, public = {}, [], {}, {}
            for algorithm, (_, selector, kind) in custody.KEYS.items():
                command = ["openssl", "genpkey", "-algorithm", algorithm.upper()]
                if algorithm == "rsa":
                    command += ["-pkeyopt", "rsa_keygen_bits:2048"]
                pem = subprocess.run(command, capture_output=True, check=True,
                                     timeout=20, env={"PATH": os.environ["PATH"]}).stdout
                keys[algorithm] = pem.decode("ascii")
                path = root / (algorithm + ".pem")
                path.write_bytes(pem)
                path.chmod(0o600)
                files.append(path)
                ident = mail.create(sc, "DkimSignature", {
                    "@type": kind, "domainId": custody.DOMAIN_ID, "selector": selector,
                    "stage": "active", "nextTransitionAt": None,
                    "privateKey": {"@type": "File", "filePath": str(path)}})
                targets[algorithm] = (ident, selector, kind)
                public[algorithm] = custody.public_key(keys[algorithm], algorithm)
            custody.KEYS = targets
            baseline = custody.migrate(api, keys)["signatures"]
            mail.create(sc, "MtaRoute", {"@type": "Relay", "name": "fixture-receiver",
                "address": RELAY, "port": receiver["ports"]["lmtp"], "protocol": "lmtp",
                "implicitTls": True, "allowInvalidCerts": True})  # fixture certificate only
            mail.update(sc, "MtaOutboundStrategy", {"route": {"else": "'fixture-receiver'", "match": {}}})
            mail.update(sc, "SenderAuth", {"dkimSignDomain": {"else": repr(DOMAIN), "match": {}}})
            mail.update(rc, "SystemSettings", {"defaultHostname": RECEIVER})
            mail.update(rc, "MtaStageData", {"addAuthResultsHeader": {"else": "true", "match": {}}})
            mail.update(rc, "SenderAuth", {field: {"else": "relaxed" if field == "dkimVerify" else "disable", "match": {}}
                for field in ("spfEhloVerify", "spfFromVerify", "dkimVerify", "dmarcVerify", "arcVerify", "reverseIpVerify")})
            mail.update(rc, "DnsResolver", {"@type": "Custom", "servers": {"0": {
                "protocol": "udp", "address": "127.0.0.1", "port": 15353}},
                "attempts": 1, "timeout": 1000, "concurrency": 2, "enableEdns": False, "tcpOnError": False})
            with local_dns(root, public):
                for fixture in fixtures:
                    mail.reload(fixture["client"])
                for phase in ("file", "text-restart"):
                    if phase == "text-restart":
                        require(custody.migrate(api, keys, apply=True)["signatures"] == baseline,
                                "Custody migration changed key identity")
                        rows = custody.read_signatures(api, include_private=True)
                        require(all(r["privateKey"] == {"@type": "Text", "secret": "****"}
                                    for r in rows.values()), "Expected masked Text custody")
                        sender["server"].stop()
                        for path in files:
                            path.unlink()
                        mail.start_mail(sender["server"])
                        require(not any(path.exists() for path in files), "Old key file survived")
                        require(custody.migrate(api, keys)["signatures"] == baseline,
                                "Restart changed signature identity")
                        require(all(row["privateKey"] == {"@type": "Text", "secret": "****"}
                                    for row in custody.read_signatures(api, include_private=True).values()),
                                "Restart did not retain masked Text custody")
                    message = mail.known_message("dkim-signing-" + phase)
                    message.replace_header("From", "alice@" + DOMAIN)
                    message.replace_header("To", "alice@" + DOMAIN)
                    raw = capture(mail, receiver, lambda: mail.smtp_send(sender, "alice@" + DOMAIN,
                                                                       message, user="alice"))
                    verify(raw)
                    for selector in ("stalwart-rsa", "stalwart-ed25519"):
                        # Capture a fresh signed probe in Bob's inbox, then submit
                        # its corrupted signature to Alice. Replaying into the
                        # same inbox triggers native Message-ID deduplication.
                        probe = mail.known_message(phase + "-" + selector)
                        probe.replace_header("From", "alice@" + DOMAIN)
                        signed = capture(mail, receiver, lambda: mail.smtp_send(
                            sender, "bob@" + DOMAIN, probe, user="alice"), user="bob")
                        verify(signed)
                        damaged = corrupt(signed, selector)
                        checked = capture(mail, receiver, lambda: mail.smtp_send(receiver, "alice@" + DOMAIN, damaged))
                        verify(checked, failed=selector)
                    print("PASS:", phase, "RSA + Ed25519 native verification; independent tamper controls", flush=True)
            print("PASS: unchanged IDs/selectors/public keys; Text signing after key-file removal and normal-mode restart")
        finally:
            for server in reversed(servers):
                server.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--fixture-directory", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.binary.resolve(), args.fixture_directory.resolve())
    except Exception as error:
        # Do not print API bodies, generated credentials or native logs.
        detail = str(error) if isinstance(error, FixtureError) else type(error).__name__ + "; diagnostics suppressed"
        print("FAIL: signing fixture: " + detail, file=sys.stderr)
        raise SystemExit(1) from None
