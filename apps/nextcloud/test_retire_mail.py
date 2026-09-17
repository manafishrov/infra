"""Exercise the embedded retirement script without contacting Nextcloud."""

import contextlib
import io
import json
from pathlib import Path
import textwrap
import unittest


class RetireMailTest(unittest.TestCase):
    def setUp(self):
        config = Path(__file__).with_name("configmap.yaml").read_text()
        source = config.split("  retire-mail.py: |\n", 1)[1].split("  bootstrap.sh: |\n", 1)[0]
        self.script = {"__name__": "retire_mail_test"}
        exec(compile(textwrap.dedent(source), "retire-mail.py", "exec"), self.script)
        self.calls = []
        self.enabled = True
        self.installed = True
        self.fail = None
        self.accounts = {
            "alice": [{"id": 1, "provision": {"status": "none"}}],
            "bob": [{"id": 2, "provision": {"status": "none"}}],
        }
        self.script["occ"] = self.occ

    def occ(self, *args):
        self.calls.append(args)
        command = args[0]
        if command == self.fail:
            raise RuntimeError("fixture failure")
        if command == "app:list":
            return json.dumps({"enabled" if self.enabled else "disabled": {"mail": "5"} if self.installed else {}})
        if command == "user:list":
            self.assertIn("--limit=0", args)
            return json.dumps(dict.fromkeys(self.accounts, "name"))
        if command == "mail:account:export":
            return json.dumps(self.accounts[args[1]])
        if command == "mail:account:delete":
            for user, accounts in self.accounts.items():
                self.accounts[user] = [a for a in accounts if str(a["id"]) != args[1]]
        return ""

    def retire(self, apply):
        with contextlib.redirect_stdout(io.StringIO()):
            self.script["retire"](apply)

    def test_dry_run_never_mutates(self):
        self.retire(False)
        self.assertTrue(all(call[0] in {"app:list", "user:list", "mail:account:export"} for call in self.calls))

    def test_remove_follows_deletion_cleanup_and_empty_inventory(self):
        self.retire(True)
        self.assertEqual(self.calls[-1], ("app:remove", "mail"))
        self.assertEqual([c for c in self.calls if c[0] == "mail:account:delete"], [("mail:account:delete", "1"), ("mail:account:delete", "2")])
        cleanup = self.calls.index(("mail:clean-up",))
        self.assertEqual(self.calls[cleanup + 1:-1], [("mail:account:export", "alice", "--output=json"), ("mail:account:export", "bob", "--output=json")])

    def test_provisioned_account_blocks_all_deletion(self):
        self.accounts["bob"][0]["provision"]["status"] = "set"
        with self.assertRaises(RuntimeError):
            self.retire(True)
        self.assertFalse(any(c[0] in {"mail:account:delete", "app:remove"} for c in self.calls))

    def test_duplicate_ids_block_deletion(self):
        self.accounts["bob"][0]["id"] = 1
        with self.assertRaises(RuntimeError):
            self.retire(True)
        self.assertFalse(any(c[0] == "mail:account:delete" for c in self.calls))

    def test_failed_cleanup_preserves_app_cli(self):
        self.fail = "mail:clean-up"
        with self.assertRaises(RuntimeError):
            self.retire(True)
        self.assertNotIn(("app:remove", "mail"), self.calls)

    def test_disabled_dry_run_does_not_enable(self):
        self.enabled = False
        with self.assertRaises(RuntimeError):
            self.retire(False)
        self.assertNotIn(("app:enable", "mail"), self.calls)

    def test_absent_app_is_noop(self):
        self.installed = False
        self.retire(True)
        self.assertEqual(self.calls, [("app:list", "--output=json")])


if __name__ == "__main__":
    unittest.main()
