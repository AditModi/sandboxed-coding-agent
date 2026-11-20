"""The five GitHub REST calls the broker needs to open a pull request, with the standard
library only. No git binary, no clone: the broker never holds the repository, only the
files the request changes. Docs: https://docs.github.com/en/rest/git"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

API = "https://api.github.com"


class GitHubError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"GitHub answered {status}: {message}")
        self.status = status


class GitHub:
    def __init__(self, repo: str, token: str, api: str | None = None) -> None:
        self.repo, self._token, self.api = repo, token, api or API

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        request = urllib.request.Request(
            f"{self.api}/repos/{self.repo}{path}",
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "sandboxed-coding-agent-broker",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            try:
                message = json.load(error).get("message", "")
            except ValueError:
                message = error.reason
            raise GitHubError(error.code, message) from None

    def open_pull_request(self, base: str, pr) -> dict:
        base_sha = self._call("GET", f"/git/ref/heads/{base}")["object"]["sha"]
        base_tree = self._call("GET", f"/git/commits/{base_sha}")["tree"]["sha"]
        tree = self._call("POST", "/git/trees", {
            "base_tree": base_tree,
            "tree": [{"path": p, "mode": "100644", "type": "blob", "content": c}
                     for p, c in sorted(pr.files.items())],
        })["sha"]
        commit = self._call("POST", "/git/commits", {
            "message": pr.title, "tree": tree, "parents": [base_sha]})["sha"]
        # Creating the ref fails with 422 if the branch exists, so the agent can never
        # move a branch, only create a new one under the prefix.
        self._call("POST", "/git/refs", {"ref": f"refs/heads/{pr.branch}", "sha": commit})
        pull = self._call("POST", "/pulls", {
            "title": pr.title, "body": pr.body, "head": pr.branch, "base": base})
        return {"number": pull["number"], "url": pull["html_url"], "branch": pr.branch,
                "commit": commit}
