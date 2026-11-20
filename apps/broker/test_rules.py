import os
import unittest

from rules import Rejection, check_request, load_policy

POLICY = load_policy(os.path.join(os.path.dirname(__file__), "broker-policy.json"))


def request(**overrides):
    body = {"branch": "fix-inr-grouping", "title": "Fix Indian grouping", "body": "Fixes #1",
            "files": {"indian_numbers/money.py": "print('fixed')\n"}}
    body.update(overrides)
    return body


class Rules(unittest.TestCase):
    def assertRefused(self, req, fragment):
        with self.assertRaises(Rejection) as caught:
            check_request(req, POLICY)
        self.assertIn(fragment, caught.exception.reason)

    def test_valid_request_gets_the_prefix(self):
        self.assertEqual(check_request(request(), POLICY).branch, "agent/fix-inr-grouping")

    def test_workflow_files_are_refused(self):
        self.assertRefused(request(files={".github/workflows/release.yml": "x"}), ".github/")
        self.assertRefused(request(files={".GitHub/Workflows/ci.yml": "x"}), ".github/")

    def test_path_tricks_are_refused(self):
        for path in ("../outside.py", "a/../.github/x.yml", "/etc/passwd", "a\\b.py", "./a.py"):
            with self.assertRaises(Rejection, msg=path):
                check_request(request(files={path: "x"}), POLICY)

    def test_codeowners_is_refused(self):
        self.assertRefused(request(files={"docs/CODEOWNERS": "* @me"}), "CODEOWNERS")

    def test_request_cannot_choose_base_or_repo(self):
        self.assertRefused(request(base="main"), "unexpected field")
        self.assertRefused(request(repo="someone/else"), "unexpected field")

    def test_branch_cannot_escape_the_prefix(self):
        for branch in ("main", "../main", "Agent/x", "a" * 42, "fix/inr"):
            if branch == "main":
                # 'main' is a valid NAME; it becomes agent/main, never main itself.
                self.assertEqual(check_request(request(branch=branch), POLICY).branch, "agent/main")
                continue
            with self.assertRaises(Rejection, msg=branch):
                check_request(request(branch=branch), POLICY)

    def test_limits(self):
        many = {f"f{i}.py": "x" for i in range(11)}
        self.assertRefused(request(files=many), "files must map")
        self.assertRefused(request(files={"big.py": "x" * 100_001}), "over 100000 bytes")
        self.assertRefused(request(title=""), "title")


if __name__ == "__main__":
    unittest.main()
