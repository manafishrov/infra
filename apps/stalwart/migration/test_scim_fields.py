"""Offline safety checks for the operator's SCIM capture/restore helper."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("scim_fields", Path(__file__).with_name("scim-fields.py"))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ScimFieldsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / "scim-fields.json"
        self.rows = {
            "x:Account": [{"id": str(i), "@type": "Group" if i == 0 else "User",
                           "name": f"account-{i}", "domainId": "c",
                           "externalId": None if i == 0 else f"external-{i}",
                           "permissions": {"@type": "Inherit"}}
                          for i in range(101)],
            "x:Domain": [{"id": "c", "name": "example.com", "allowScimProvisioning": True},
                         {"id": "b", "name": "system.example.com", "allowScimProvisioning": False}],
        }
        self.rows["x:Account"][1]["permissions"] = {
            "@type": "Replace", "disabledPermissions": {},
            "enabledPermissions": {"authenticate": True, "scimAccess": True}}
        self.writes = []
        self.refuse_updates = False
        self.authorizations = set()

    def urlopen(self, req, timeout):
        self.authorizations.add(req.get_header("Authorization"))
        if req.data is None:
            body = {"primaryAccounts": {"urn:stalwart:jmap": "admin"},
                    "apiUrl": "https://mail.example.com/jmap/"}
        elif not req.full_url.startswith("https://mail.manafishrov.com/"):
            raise AssertionError(f"request left --url: {req.full_url}")
        else:
            method, args, call_id = json.loads(req.data)["methodCalls"][0]
            kind, action = method.split("/")
            if action == "query":
                start = args["position"]
                result = {"ids": [r["id"] for r in self.rows[kind]][start:start + args["limit"]],
                          "total": len(self.rows[kind])}
            elif action == "get":
                result = {"list": [copy.deepcopy(r) for r in self.rows[kind] if r["id"] in args["ids"]]}
            elif self.refuse_updates:
                result = {"notUpdated": {next(iter(args["update"])): {"type": "forbidden"}}}
            else:
                self.writes.append(args["update"])
                for row in self.rows[kind]:
                    row.update(args["update"].get(row["id"], {}))
                result = {"updated": {key: None for key in args["update"]}}
            body = {"methodResponses": [[method, result, call_id]]}
        return io.StringIO(json.dumps(body))

    def run_helper(self, action, env=None):
        old_umask = os.umask(0o077)
        self.addCleanup(os.umask, old_umask)
        with patch.object(helper, "urlopen", self.urlopen), \
             patch.dict(os.environ, env or {"STALWART_TOKEN": "fixture-token"}, clear=True), \
             patch("sys.argv", ["scim-fields.py", action, str(self.file)]), \
             contextlib.redirect_stdout(io.StringIO()):
            helper.main()

    def test_round_trip_pages_groups_null_and_false(self):
        original = copy.deepcopy(self.rows)
        self.run_helper("capture")
        self.assertEqual(self.file.stat().st_mode & 0o777, 0o600)
        for row in self.rows["x:Account"]:
            row["externalId"] = "lost"
        for row in self.rows["x:Domain"]:
            row["allowScimProvisioning"] = not row["allowScimProvisioning"]
        del self.rows["x:Account"][1]["permissions"]["enabledPermissions"]["scimAccess"]
        with self.assertRaisesRegex(RuntimeError, "SCIM value differs"):
            self.run_helper("verify")
        self.run_helper("restore")
        self.assertEqual(self.rows, original)
        self.run_helper("verify")

    def test_missing_scim_access_fails_verify(self):
        self.run_helper("capture")
        del self.rows["x:Account"][1]["permissions"]["enabledPermissions"]["scimAccess"]
        with self.assertRaisesRegex(RuntimeError, "scimAccess missing"):
            self.run_helper("verify")

    def test_suspended_account_refuses_capture(self):
        self.rows["x:Account"][2]["permissions"] = {
            "@type": "Replace", "enabledPermissions": {},
            "disabledPermissions": {"authenticate": True}}
        with self.assertRaisesRegex(RuntimeError, "suspended"):
            self.run_helper("capture")
        self.assertFalse(self.file.exists())

    def test_recovery_admin_uses_basic_auth(self):
        self.run_helper("capture", {"STALWART_RECOVERY_ADMIN": "admin:secret"})
        self.assertEqual(self.authorizations, {"Basic YWRtaW46c2VjcmV0"})

    def test_capture_never_overwrites_original(self):
        self.run_helper("capture")
        original = self.file.read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_helper("capture")
        self.assertEqual(self.file.read_bytes(), original)

    def test_missing_source_field_refuses_capture(self):
        del self.rows["x:Account"][0]["externalId"]
        with self.assertRaisesRegex(RuntimeError, "SCIM field missing"):
            self.run_helper("capture")
        self.assertFalse(self.file.exists())

    def test_changed_identity_refuses_restore(self):
        self.run_helper("capture")
        self.rows["x:Account"][0]["name"] = "different-account"
        with self.assertRaisesRegex(RuntimeError, "identity changed"):
            self.run_helper("restore")
        self.assertEqual(self.writes, [])

    def test_jmap_update_error_is_not_success(self):
        self.run_helper("capture")
        self.refuse_updates = True
        with self.assertRaisesRegex(RuntimeError, "notUpdated"):
            self.run_helper("restore")


if __name__ == "__main__":
    unittest.main()
