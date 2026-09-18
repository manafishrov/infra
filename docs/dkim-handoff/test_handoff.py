#!/usr/bin/env python3
"""Offline custody tests; optional real-provider tests use a loopback fake API only."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("custody", HERE / "custody.py")
custody = importlib.util.module_from_spec(spec)
spec.loader.exec_module(custody)


class FakeNative:
    def __init__(self, keys):
        self.manual = True
        self.writes = []
        self.partial = False
        self.ignore_write = False
        self.rows = {}
        for algorithm, (key_id, selector, kind) in custody.KEYS.items():
            self.rows[key_id] = {
                "id": key_id, "@type": kind, "domainId": "c", "selector": selector,
                "stage": "active", "nextTransitionAt": None,
                "publicKey": custody.public_key(keys[algorithm], algorithm),
                "headers": ["From", "Date"], "canonicalization": "relaxed/relaxed",
                "privateKey": {"@type": "File", "filePath": "/original.key"},
            }

    def call(self, method, args):
        if method == "x:Domain/get":
            return {"list": [{"id": "c", "name": "manafishrov.com", "dkimManagement": {
                "@type": "Manual" if self.manual else "Automatic"}}]}
        if method == "x:DkimSignature/get":
            rows = [{k: copy.deepcopy(v) for k, v in self.rows[key_id].items()
                     if k in args["properties"]} for key_id in args["ids"]]
            for row in rows:
                if row.get("privateKey", {}).get("@type") == "Text":
                    row["privateKey"]["secret"] = "****"
            return {"list": rows}
        if method == "x:DkimSignature/set":
            self.writes.append(copy.deepcopy(args))
            if self.partial:
                return {"updated": {}, "notUpdated": {"redacted": {"description": "secret"}}}
            if not self.ignore_write:
                for key_id, update in args["update"].items():
                    self.rows[key_id].update(copy.deepcopy(update))
            return {"updated": {key: None for key in args["update"]}}
        raise AssertionError("Unexpected native method")


class CustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys = {}
        for algorithm in custody.KEYS:
            args = ["openssl", "genpkey", "-algorithm", algorithm.upper()]
            if algorithm == "rsa":
                args += ["-pkeyopt", "rsa_keygen_bits:2048"]
            cls.keys[algorithm] = subprocess.run(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                env={"PATH": os.environ.get("PATH", "")},
            ).stdout.decode()

    def test_check_never_sets(self):
        api = FakeNative(self.keys)
        self.assertEqual(custody.migrate(api, self.keys)["mode"], "checked")
        self.assertEqual(api.writes, [])

    def test_exact_bytes_text_and_idempotence(self):
        keys = dict(self.keys)
        keys["rsa"] = keys["rsa"].replace("\n", "\r\n")
        api = FakeNative(keys)
        for _ in range(2):
            result = custody.migrate(api, keys, apply=True)
            self.assertEqual(result["mode"], "imported")
            self.assertNotIn("PRIVATE KEY", json.dumps(result))
        for algorithm, (key_id, _, _) in custody.KEYS.items():
            self.assertEqual(api.writes[0]["update"][key_id], {
                "privateKey": {"@type": "Text", "secret": keys[algorithm]}})

    def test_all_preconditions_before_any_write(self):
        for mutate in (
            lambda a: setattr(a, "manual", False),
            lambda a: a.rows["jdzlxs2uamqa"].update(selector="resend"),
            lambda a: a.rows["jdzlxs2uamqa"].update(stage="pending"),
            lambda a: a.rows["jdzlxs2uamqa"].update(nextTransitionAt="2026-01-01T00:00:00Z"),
            lambda a: a.rows["jdzlxs2uamqa"].update(publicKey="wrong-key"),
        ):
            api = FakeNative(self.keys)
            mutate(api)
            with self.assertRaises(custody.HandoffError):
                custody.migrate(api, self.keys, apply=True)
            self.assertEqual(api.writes, [])

    def test_partial_or_ignored_write_fails(self):
        for flag in ("partial", "ignore_write"):
            api = FakeNative(self.keys)
            setattr(api, flag, True)
            with self.assertRaises(custody.HandoffError):
                custody.migrate(api, self.keys, apply=True)

    def test_endpoint_and_redirect_restrictions(self):
        for endpoint in ("http://localhost", "https://user:password@example.com",
                         "https://example.com/other", "https://example.com?token=x"):
            with self.assertRaises(custody.HandoffError):
                custody.NativeAPI(endpoint, "fixture-token")
        with self.assertRaises(custody.HandoffError):
            custody.NoRedirect().redirect_request(None, None, 302, None, None, "https://other")

    def test_cli_does_not_echo_malformed_secret_input(self):
        result = subprocess.run(
            ["python3", "-B", str(HERE / "custody.py"), "--endpoint", "https://unused.invalid"],
            input='{"rsa":"PRIVATE-SENTINEL', text=True, capture_output=True,
            env={"PATH": os.environ["PATH"], "STALWART_TOKEN": "TOKEN-SENTINEL"},
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("SENTINEL", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_requires_release_gates_before_input_or_network(self):
        result = subprocess.run(
            ["python3", "-B", str(HERE / "custody.py"), "--endpoint", "https://unused.invalid", "--apply"],
            input="", text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--ownership-released", result.stderr)


class FinalConfigurationTests(unittest.TestCase):
    def test_native_keys_and_dns_are_no_longer_terraform_managed(self):
        native = "\n".join(path.read_text() for path in (ROOT / "tofu/stalwart").glob("*.tf"))
        self.assertNotRegex(native, r'resource\s+"stalwart_dkim_signature')
        self.assertNotRegex(native, r'\bto\s*=\s*stalwart_dkim_signature')
        dns = (ROOT / "tofu/dns/main.tf").read_text()
        variables = (ROOT / "tofu/dns/variables.tf").read_text()
        for algorithm in custody.KEYS:
            self.assertNotIn("stalwart_dkim_" + algorithm, dns)
            self.assertNotIn("dkim_" + algorithm + "_pub_manafishrov", variables)
        self.assertIn("resend_dkim =", dns)
        self.assertFalse(list((HERE / "stages").glob("*.patch")))

    def test_non_destructive_ownership_receipts_remain(self):
        for stack, prefix in (("stalwart", "stalwart_dkim_signature_dkim1_"),
                              ("dns", "cloudflare_dns_record.stalwart_dkim_")):
            receipt = (ROOT / "tofu" / stack / "handoff.tf").read_text()
            removed = re.findall(r'removed\s*\{\s*from\s*=\s*(\S+)\s*'
                                 r'lifecycle\s*\{\s*destroy\s*=\s*false\s*\}\s*\}', receipt)
            expected = ([prefix + algorithm + "_sha256.manafishrov" for algorithm in custody.KEYS]
                        if stack == "stalwart" else
                        [prefix + algorithm + "_handoff" for algorithm in custody.KEYS])
            self.assertCountEqual(removed, expected)
            self.assertEqual(len(re.findall(r'\bremoved\s*\{', receipt)), 2)
            self.assertNotRegex(receipt, r'destroy\s*=\s*true')
            if stack == "dns":
                for algorithm in custody.KEYS:
                    self.assertRegex(receipt, r'moved\s*\{\s*from\s*=\s*'
                                     r'cloudflare_dns_record\.manafishrov\["stalwart_dkim_' + algorithm +
                                     r'"\]\s*to\s*=\s*cloudflare_dns_record\.stalwart_dkim_' +
                                     algorithm + r'_handoff\s*\}')

    def test_manual_rotation_certificates_and_dkim_only_publication(self):
        main = (ROOT / "tofu/stalwart/main.tf").read_text()
        domain = main.split('resource "stalwart_domain" "manafishrov" {', 1)[1].split('\n}', 1)[0]
        for field in ("dkim_management", "certificate_management", "dns_management"):
            block = re.search(r'\b' + field + r'\s*=\s*\{([^}]*)\}', domain).group(1)
            if field == "dns_management":
                self.assertRegex(block, r'type\s*=\s*"Automatic"')
                self.assertRegex(block, r'publish_records\s*=\s*\["dkim"\]')
                self.assertRegex(block, r'origin\s*=\s*"manafishrov\.com"')
                self.assertRegex(block, r'dns_server_id\s*=\s*stalwart_dns_server_cloudflare\.dkim\.id')
            else:
                self.assertRegex(block, r'type\s*=\s*"Manual"')
        for block in re.findall(r'(?:dkim_management|certificate_management)\s*=\s*\{([^}]*)\}', main):
            self.assertRegex(block, r'type\s*=\s*"Manual"')

    def test_environment_provider_and_no_old_key_mount(self):
        provider = (ROOT / "tofu/stalwart/dns.tf").read_text()
        secret = re.search(r'\bsecret\s*=\s*\{([^}]*)\}', provider).group(1)
        self.assertRegex(secret, r'type\s*=\s*"EnvironmentVariable"')
        self.assertRegex(secret, r'variable_name\s*=\s*"STALWART_CLOUDFLARE_DKIM_TOKEN"')
        self.assertNotRegex(secret, r'\b(?:secret|file_path)\s*=')
        workload = (ROOT / "apps/stalwart/statefulset.yaml").read_text()
        self.assertNotIn("stalwart-dkim", workload)
        self.assertNotIn("private/dkim", workload)
        self.assertRegex(workload, r'secretRef:\s*name: stalwart-env')
        self.assertIn("secretName: wildcard-tls", workload)


@unittest.skipUnless(all(os.environ.get(key) for key in (
    "CF_PROVIDER_MIRROR", "DNS_UPDATE_SOURCE", "RUSTC")) and any(os.environ.get(key) for key in (
    "TOFU_1_11_5", "TOFU_RUNNER_1_12_1")),
    "set a qualified TOFU binary, CF_PROVIDER_MIRROR, DNS_UPDATE_SOURCE and RUSTC")
class CloudflareProviderTests(unittest.TestCase):
    def test_normalization_put_and_declarative_forget(self):
        """Run real 5.22.0 against fake records; never use credentials or the public API."""
        for key, version in (("TOFU_1_11_5", "1.11.5"), ("TOFU_RUNNER_1_12_1", "1.12.1")):
            if tofu := os.environ.get(key):
                with self.subTest(version=version):
                    self.assertIn("OpenTofu v" + version,
                                  subprocess.check_output([tofu, "version"], text=True))
                    self.check_provider(tofu)

    def check_provider(self, tofu):
        zone = "a" * 32
        public_keys = {"rsa": "A" * 392, "ed25519": "B" * 43 + "=", "resend": "UNCHANGED"}
        records = {}
        for index, algorithm in enumerate(("rsa", "ed25519", "resend"), 1):
            records[str(index) * 32] = {
                "id": str(index) * 32, "zone_id": zone, "zone_name": "example.invalid",
                "name": f"{algorithm}._domainkey.example.invalid", "type": "TXT", "ttl": 300,
                "content": f"v=DKIM1; k={algorithm}; p={public_keys[algorithm]}",
                "proxied": False, "proxiable": False, "tags": [], "settings": {},
                "created_on": "2026-01-01T00:00:00Z", "modified_on": "2026-01-01T00:00:00Z",
            }
        original_resend = copy.deepcopy(records["3" * 32])
        events = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, value, status=200):
                body = json.dumps({"success": status == 200, "errors": [], "messages": [], "result": value}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                events.append(("GET", self.path))
                if self.path.startswith(f"/zones/{zone}/dns_records/"):
                    self.reply(records[self.path.rsplit("/", 1)[1]])
                else:
                    self.reply(None, 404)

            def do_PUT(self):
                events.append(("PUT", self.path))
                key = self.path.rsplit("/", 1)[1]
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                records[key].update(data)
                self.reply(records[key])

            def do_DELETE(self):
                events.append(("DELETE", self.path))
                self.reply(None, 500)

            def do_POST(self):
                events.append(("POST", self.path))
                self.reply(None, 500)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="dkim-cloudflare-") as name:
                work = Path(name)
                # Compile the actual pinned dependency function, not a Python reimplementation.
                source = Path(os.environ["DNS_UPDATE_SOURCE"])
                self.assertIn('version = "0.5.7"', (source / "Cargo.toml").read_text())
                utils = (source / "src/utils.rs").read_text()
                formatter = utils[utils.index("const MAX_CHUNK_BYTES:"):utils.index("pub(crate) fn txt_chunks(")]
                cloudflare = (source / "src/providers/cloudflare.rs").read_text()
                self.assertIn('txt_chunks_to_text(&mut out, &content, " ");', cloudflare)
                (work / "txt.rs").write_text(formatter + '''
fn main() {
    let input = std::env::args().nth(1).unwrap();
    let mut output = String::new();
    txt_chunks_to_text(&mut output, &input, " ");
    print!("{}", output);
}
''')
                compiled = subprocess.run([os.environ["RUSTC"], str(work / "txt.rs"), "-o", str(work / "txt")],
                                          text=True, capture_output=True)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                expected = {algorithm: subprocess.check_output([
                    str(work / "txt"), f"v=DKIM1; k={algorithm}; h=sha256; p={public_keys[algorithm]}"
                ], text=True) for algorithm in ("rsa", "ed25519")}
                self.assertIn('\" \"', expected["rsa"])  # RSA crosses the 255-byte boundary.
                self.assertNotIn('\" \"', expected["ed25519"])
                # Retain the historical normalization expression as a standalone
                # fixture. Active Terraform deliberately no longer owns these keys.
                # Only fake public data enters the temporary provider state.
                native_locals = r'''variable "public_keys" {
  type = map(string)
}
locals {
  stalwart_dkim_txt = {
    for algorithm, key in var.public_keys : algorithm => "v=DKIM1; k=${algorithm}; h=sha256; p=${key}"
  }
  stalwart_dkim_cloudflare_txt = {
    for algorithm, text in local.stalwart_dkim_txt : algorithm => join(" ", [
      for chunk in regexall(".{1,255}", text) : format("\"%s\"", chunk)
    ])
  }
}
'''
                (work / "fixture.auto.tfvars.json").write_text(json.dumps({
                    "public_keys": {algorithm: public_keys[algorithm] for algorithm in ("rsa", "ed25519")},
                }))
                mirror = str(Path(os.environ["CF_PROVIDER_MIRROR"]).resolve())
                (work / "tofurc").write_text('provider_installation {\n filesystem_mirror {\n'
                    f' path = {json.dumps(mirror)}\n include = ["registry.opentofu.org/cloudflare/cloudflare"]\n'
                    ' }\n}\n')
                # No inherited API tokens, proxy settings, CLI flags or real backends.
                env = {"PATH": os.environ["PATH"], "HOME": str(work),
                       "TF_CLI_CONFIG_FILE": str(work / "tofurc"), "CHECKPOINT_DISABLE": "1"}

                def run(*args):
                    result = subprocess.run([tofu, f"-chdir={work}", *args], env=env,
                                            text=True, capture_output=True, timeout=90)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    return result.stdout

                def config(normalized, forget=False):
                    items = {}
                    for algorithm in ("rsa", "ed25519", "resend"):
                        if forget and algorithm != "resend":
                            continue
                        items[algorithm] = f"v=DKIM1; k={algorithm}; p={public_keys[algorithm]}"
                    each = f"jsondecode({json.dumps(json.dumps(items))})"
                    if normalized and not forget:
                        each = 'merge(local.stalwart_dkim_cloudflare_txt, { resend = ' + json.dumps(items["resend"]) + ' })'
                    text = native_locals + f'''terraform {{
  required_version = "~> 1.11.5"
  required_providers {{
    cloudflare = {{ source = "cloudflare/cloudflare", version = "5.22.0" }}
  }}
}}
provider "cloudflare" {{
  api_token = "{'x' * 40}"
  base_url = "http://127.0.0.1:{server.server_port}/"
}}
resource "cloudflare_dns_record" "records" {{
  for_each = {each}
  zone_id = "{zone}"
  name = "${{each.key}}._domainkey.example.invalid"
  type = "TXT"
  ttl = 300
  content = each.value
}}
'''
                    if forget:
                        for algorithm in ("rsa", "ed25519"):
                            text += f'''moved {{
  from = cloudflare_dns_record.records["{algorithm}"]
  to = cloudflare_dns_record.{algorithm}_handoff
}}
removed {{
  from = cloudflare_dns_record.{algorithm}_handoff
  lifecycle {{ destroy = false }}
}}
'''
                    (work / "main.tf").write_text(text)

                config(False)
                run("init", "-backend=false", "-input=false", "-no-color")
                for index, algorithm in enumerate(("rsa", "ed25519", "resend"), 1):
                    run("import", "-input=false", "-no-color",
                        f'cloudflare_dns_record.records["{algorithm}"]', f"{zone}/{str(index) * 32}")
                events.clear()
                config(True)
                run("plan", "-out=phase0.tfplan", "-input=false", "-no-color")
                plan = json.loads(run("show", "-json", "phase0.tfplan"))
                changes = {r["address"]: r["change"]["actions"] for r in plan["resource_changes"]}
                self.assertEqual(changes, {
                    'cloudflare_dns_record.records["rsa"]': ["update"],
                    'cloudflare_dns_record.records["ed25519"]': ["update"],
                    'cloudflare_dns_record.records["resend"]': ["no-op"],
                })
                run("apply", "-input=false", "-no-color", "phase0.tfplan")
                mutations = [(method, path) for method, path in events if method != "GET"]
                self.assertCountEqual(mutations, [("PUT", f"/zones/{zone}/dns_records/{str(i) * 32}") for i in (1, 2)])
                for index, algorithm in enumerate(("rsa", "ed25519"), 1):
                    self.assertEqual(records[str(index) * 32]["id"], str(index) * 32)
                    self.assertEqual(records[str(index) * 32]["content"], expected[algorithm])
                events.clear()
                config(True, forget=True)
                run("plan", "-out=release.tfplan", "-input=false", "-no-color")
                plan = json.loads(run("show", "-json", "release.tfplan"))
                self.assertCountEqual([r["change"]["actions"] for r in plan["resource_changes"]],
                                      [["forget"], ["forget"], ["no-op"]])
                run("apply", "-input=false", "-no-color", "release.tfplan")
                self.assertEqual([m for m in events if m[0] != "GET"], [])
                self.assertEqual(run("state", "list").strip(), 'cloudflare_dns_record.records["resend"]')
                self.assertEqual(records["3" * 32], original_resend)
                self.assertEqual(len(records), 3)
                self.assertIn("No changes", run("plan", "-input=false", "-no-color"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
