#!/usr/bin/env python3
"""Exercise custody on a real OSS binary, only in a loopback-only network namespace.

Uses ephemeral Recovery mode, no Account creation, no DNS provider or mail listener.
All generated fixture keys, configuration and database live in /tmp.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.request

import custody


APPROVED_SHA256 = "02030a8334e3bc62bae1fa4a9139f498df0a7e105bd97ec5beacfdfa1be8b614"


class RecoveryAPI:
    def __init__(self, port, password):
        self.origin = f"http://127.0.0.1:{port}"
        self.auth = "Basic " + base64.b64encode(("fixture:" + password).encode()).decode()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), custody.NoRedirect())

    def request(self, path, body=None):
        request = urllib.request.Request(
            self.origin + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": self.auth, "Content-Type": "application/json"},
        )
        with self.opener.open(request, timeout=10) as response:
            return json.load(response)

    def call(self, method, args):
        response = self.request("/jmap", {
            "using": ["urn:ietf:params:jmap:core", "urn:stalwart:jmap"],
            "methodCalls": [[method, args, "fixture"]],
        })["methodResponses"]
        if len(response) != 1 or response[0][0] != method:
            raise RuntimeError("Native fixture method failed; response suppressed")
        result = response[0][1]
        if any(result.get(key) for key in ("notCreated", "notUpdated", "notDestroyed")):
            raise RuntimeError("Native fixture Set failed; response suppressed")
        return result


def run(binary):
    links = json.loads(subprocess.check_output(["ip", "-j", "link", "show"]))
    if len(links) != 1 or links[0]["ifname"] != "lo":
        raise RuntimeError("Refusing to run without a loopback-only network namespace")
    with open(binary, "rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != APPROVED_SHA256:
            raise RuntimeError("Refusing a binary other than the approved deployment artifact")
    if subprocess.check_output([binary, "--version"], text=True).strip() != "0.16.21":
        raise RuntimeError("Expected the OSS native-SCIM 0.16.21 fixture binary")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    password = secrets.token_urlsafe(32)
    api = RecoveryAPI(port, password)
    process = None
    with tempfile.TemporaryDirectory(prefix="dkim-native-") as name:
        root = Path(name)
        config = root / "config.json"
        config.write_text(json.dumps({"@type": "RocksDb", "path": str(root / "data")}))
        env = {
            "PATH": os.environ["PATH"], "HOME": str(root), "TMPDIR": str(root),
            "XDG_CACHE_HOME": str(root / "cache"), "LANG": "C.UTF-8",
            "STALWART_RECOVERY_MODE": "true",
            "STALWART_RECOVERY_MODE_PORT": str(port),
            "STALWART_RECOVERY_ADMIN": "fixture:{PLAIN}" + password,
        }

        def stop():
            nonlocal process
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                process = None

        def start():
            nonlocal process
            process = subprocess.Popen([binary, "--config", str(config)], env=env,
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Native fixture exited before readiness")
                try:
                    account = api.request("/api/account")
                    if account.get("edition") != "oss":
                        raise RuntimeError("Native fixture is not OSS")
                    return
                except OSError:
                    time.sleep(0.2)
            raise RuntimeError("Native fixture did not become ready")

        try:
            start()
            domain = api.call("x:Domain/set", {"create": {"fixture": {
                "name": "manafishrov.com", "isEnabled": True,
                "dkimManagement": {"@type": "Manual"},
                "dnsManagement": {"@type": "Manual"},
                "certificateManagement": {"@type": "Manual"},
            }}})["created"]["fixture"]["id"]
            custody.DOMAIN_ID = domain
            keys, files, targets = {}, [], {}
            for algorithm, (_, selector, kind) in custody.KEYS.items():
                args = ["openssl", "genpkey", "-algorithm", algorithm.upper()]
                if algorithm == "rsa":
                    args += ["-pkeyopt", "rsa_keygen_bits:2048"]
                pem = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     env={"PATH": os.environ["PATH"]}, check=True).stdout
                keys[algorithm] = pem.decode("ascii")
                path = root / (algorithm + ".pem")
                path.write_bytes(pem)
                path.chmod(0o600)
                files.append(path)
                key_id = api.call("x:DkimSignature/set", {"create": {"fixture": {
                    "@type": kind, "domainId": domain, "selector": selector,
                    "stage": "active", "nextTransitionAt": None,
                    "privateKey": {"@type": "File", "filePath": str(path)},
                }}})["created"]["fixture"]["id"]
                targets[algorithm] = (key_id, selector, kind)
            custody.KEYS = targets
            custody.migrate(api, keys, apply=False)
            receipt = custody.migrate(api, keys, apply=True)
            for row in custody.read_signatures(api, include_private=True).values():
                if row["privateKey"] != {"@type": "Text", "secret": "****"}:
                    raise RuntimeError("Expected masked native Text readback")
            # Force cache loss and remove the old dependency before another read.
            stop()
            for path in files:
                path.unlink()
            start()
            checked = custody.migrate(api, keys, apply=False)
            if checked["signatures"] != receipt["signatures"]:
                raise RuntimeError("Public key identity changed after restart")
            custody.migrate(api, keys, apply=True)  # idempotent with masked readback
            print("PASS: real OSS 0.16.21 File -> Text, masked readback, restart without key files, idempotent retry")
        finally:
            stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    args = parser.parse_args()
    run(str(Path(args.binary).resolve()))
