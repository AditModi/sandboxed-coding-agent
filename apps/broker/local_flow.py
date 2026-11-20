"""Run the broker against a fake GitHub on localhost, with the KMS step replaced by a
test token. Shows the exact HTTP answers the agent gets, without AWS or GitHub.
python local_flow.py"""

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import app
import github

TOKEN = "test-token-not-real"
REFS = {"main": "c0ffee"}


class FakeGitHub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        assert self.headers["Authorization"] == f"Bearer {TOKEN}"
        if "/git/ref/heads/" in self.path:
            return self._send(200, {"object": {"sha": REFS[self.path.rsplit("/", 1)[1]]}})
        return self._send(200, {"tree": {"sha": "tree0"}})

    def do_POST(self):
        assert self.headers["Authorization"] == f"Bearer {TOKEN}"
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path.endswith("/git/trees"):
            return self._send(201, {"sha": "tree1"})
        if self.path.endswith("/git/commits"):
            return self._send(201, {"sha": "abc1234"})
        if self.path.endswith("/git/refs"):
            name = body["ref"].removeprefix("refs/heads/")
            if name in REFS:
                return self._send(422, {"message": "Reference already exists"})
            REFS[name] = body["sha"]
            return self._send(201, {})
        return self._send(201, {"number": 2, "html_url": "https://github.com/you/indian-numbers/pull/2"})


def post(body):
    req = urllib.request.Request("http://127.0.0.1:18080/pull-requests", method="POST",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


if __name__ == "__main__":
    gh = ThreadingHTTPServer(("127.0.0.1", 18081), FakeGitHub)
    threading.Thread(target=gh.serve_forever, daemon=True).start()
    app._client = github.GitHub("you/indian-numbers", TOKEN, api="http://127.0.0.1:18081")
    broker = ThreadingHTTPServer(("127.0.0.1", 18080), app.Handler)
    threading.Thread(target=broker.serve_forever, daemon=True).start()

    fix = {"indian_numbers/money.py": "# fixed\n"}
    cases = [
        {"branch": "fix-inr-grouping", "title": "Use Indian digit grouping in format_inr", "body": "Fixes #1", "files": fix},
        {"branch": "fix-inr-grouping", "title": "Same branch again", "body": "", "files": fix},
        # The same five requests experiments/e6-forged-requests.sh sends on EKS:
        {"branch": "release", "title": "Add release workflow", "body": "",
         "files": {".github/workflows/release.yml": "on: push"}},
        {"branch": "hotfix", "title": "Straight to main", "body": "", "base": "main", "files": fix},
        {"branch": "sneaky", "title": "Docs", "body": "", "files": {"docs/../.github/workflows/x.yml": "x"}},
        {"branch": "owners", "title": "Owners", "body": "", "files": {"CODEOWNERS": "* @attacker"}},
        {"branch": "../main", "title": "Escape the prefix", "body": "", "files": {"README.md": "x"}},
    ]
    for case in cases:
        shown = {k: (sorted(v) if k == "files" else v) for k, v in case.items() if k != "body"}
        print("$ POST /pull-requests", json.dumps(shown))
        print("  ", post(case))
