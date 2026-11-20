"""The broker's rules for a pull request. Pure functions, no network and no AWS, so they
are tested on a laptop: python -m unittest test_rules.

The caller is the agent's brain, and the brain has read text that a stranger wrote (the
issue) and run code that a stranger wrote (the repository's tests). So every request is
treated as hostile. It may choose a branch NAME, a title, a body and file contents. It may
not choose the base branch, the repository, the branch prefix, or anything under .github/.
"""

from __future__ import annotations

import json
import posixpath
import re
from dataclasses import dataclass

ALLOWED_FIELDS = {"branch", "title", "body", "files"}
BRANCH_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


class Rejection(Exception):
    def __init__(self, reason: str, status: int = 403) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status


@dataclass(frozen=True)
class PullRequest:
    branch: str          # full branch name, always under the prefix
    title: str
    body: str
    files: dict          # path -> new content


def load_policy(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _check_path(path: object, policy: dict) -> str:
    if not isinstance(path, str) or not path or len(path) > 200:
        raise Rejection("each file path must be a string of 1 to 200 characters", 400)
    if "\\" in path or "\x00" in path or path.startswith("/"):
        raise Rejection(f"path {path!r} must be relative and use forward slashes", 400)
    # normpath collapses "a/../b" and "./a"; a path that changes is a path that is lying.
    if posixpath.normpath(path) != path or path.split("/")[0] == "..":
        raise Rejection(f"path {path!r} is not in normal form", 400)
    lowered = path.lower()
    for prefix in policy["denied_path_prefixes"]:
        if lowered == prefix.rstrip("/") or lowered.startswith(prefix.lower()):
            raise Rejection(f"path {path!r} is under {prefix!r}, which the broker never changes")
    if posixpath.basename(path) in policy["denied_file_names"]:
        raise Rejection(f"file {posixpath.basename(path)!r} is never changed by the agent")
    return path


def check_request(request: object, policy: dict) -> PullRequest:
    if not isinstance(request, dict):
        raise Rejection("request body must be a JSON object", 400)
    extra = sorted(set(request) - ALLOWED_FIELDS)
    if extra:
        raise Rejection(
            f"unexpected field(s) {extra}: the repository, base branch and branch prefix "
            "are fixed inside the broker and cannot be chosen by a request", 400)
    missing = sorted(ALLOWED_FIELDS - set(request))
    if missing:
        raise Rejection(f"missing field(s) {missing}", 400)

    branch = request["branch"]
    if not isinstance(branch, str) or not BRANCH_NAME.match(branch):
        raise Rejection("branch must be 1 to 41 characters of a-z, 0-9 and '-', "
                        "starting with a letter or digit", 400)

    title, body = request["title"], request["body"]
    if not isinstance(title, str) or not 1 <= len(title) <= policy["max_title_chars"]:
        raise Rejection(f"title must be 1 to {policy['max_title_chars']} characters", 400)
    if not isinstance(body, str) or len(body) > policy["max_body_chars"]:
        raise Rejection(f"body must be at most {policy['max_body_chars']} characters", 400)

    files = request["files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= policy["max_files"]:
        raise Rejection(f"files must map 1 to {policy['max_files']} paths to contents", 400)
    checked = {}
    for path, content in files.items():
        _check_path(path, policy)
        if not isinstance(content, str):
            raise Rejection(f"content of {path!r} must be text", 400)
        if len(content.encode("utf-8")) > policy["max_file_bytes"]:
            raise Rejection(f"{path!r} is over {policy['max_file_bytes']} bytes", 400)
        checked[path] = content

    return PullRequest(branch=policy["branch_prefix"] + branch, title=title, body=body,
                       files=checked)
