"""The git broker: the only process that holds the GitHub token.

On start it proves to AWS KMS that it is the approved sandbox and gets the token back,
decrypted for this process alone. If KMS refuses, the broker exits and the agent simply
cannot open pull requests: the safe way to fail.

It serves POST /pull-requests. Each request goes through rules.py, then the broker opens the
pull request itself, always from a new branch under agent/, always into the base branch, in
the one repository named by GITHUB_REPO. Nothing in a request can change those three.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import github
from rules import Rejection, check_request, load_policy

HERE = os.path.dirname(os.path.abspath(__file__))
POLICY = load_policy(os.path.join(HERE, "broker-policy.json"))
REPO = os.environ.get("GITHUB_REPO", "")
MAX_BODY = 1_200_000

_client: github.GitHub | None = None


def log(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True), flush=True)


def unseal_token() -> str:
    """Attested kms:Decrypt. The plaintext only ever exists in this process's memory."""
    import boto3
    from attested_recipient import AttestedRecipient

    kms = boto3.client("kms")
    ciphertext = base64.b64decode(os.environ["GITHUB_TOKEN_CIPHERTEXT"])
    with AttestedRecipient() as recipient:
        response = kms.decrypt(KeyId=os.environ["KMS_KEY_ARN"], CiphertextBlob=ciphertext,
                               Recipient=recipient.kms_recipient)
        return recipient.unwrap(response["CiphertextForRecipient"]).decode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "broker"

    def log_message(self, *args) -> None:
        pass

    def _reply(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._reply(200, {"status": "unsealed" if _client else "sealed", "repo": REPO})
        else:
            self._reply(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/pull-requests":
            return self._reply(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY:
            return self._reply(413, {"status": "refused", "reason": "body too large or empty"})
        try:
            pr = check_request(json.loads(self.rfile.read(length)), POLICY)
        except ValueError:
            return self._reply(400, {"status": "refused", "reason": "body is not JSON"})
        except Rejection as rejection:
            log("pr_refused", reason=rejection.reason)
            return self._reply(rejection.status, {"status": "refused", "reason": rejection.reason})
        try:
            result = _client.open_pull_request(POLICY["base_branch"], pr)
        except github.GitHubError as error:
            log("github_error", status=error.status, error=str(error))
            return self._reply(502, {"status": "error", "reason": str(error)})
        log("pr_opened", **result, files=sorted(pr.files))
        return self._reply(200, {"status": "opened", **result})


def main() -> None:
    global _client
    if REPO.count("/") != 1:
        log("refusing_to_start", reason="GITHUB_REPO must be owner/name")
        sys.exit(2)
    try:
        token = unseal_token()
    except Exception as error:  # noqa: BLE001 - any failure means stay sealed
        code = getattr(error, "response", {}).get("Error", {}).get("Code", type(error).__name__)
        log("broker_sealed", reason=code, detail=str(error)[:300])
        sys.exit(1)
    _client = github.GitHub(REPO, token)
    log("broker_unsealed", repo=REPO, base=POLICY["base_branch"], prefix=POLICY["branch_prefix"])
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()


if __name__ == "__main__":
    main()
