"""Idempotent pull-request comments via the GitHub REST API.

The comment carries a stable, invisible HTML marker. On each run we look for an
existing comment containing that marker and *update* it in place, so a PR never
accumulates a stack of duplicate kicad-bot comments. Uses only the standard
library (``urllib``) to keep the package dependency-free.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

LOG = logging.getLogger("kicad_bot.pr_comment")

#: Stable marker used to find-and-update our own comment. Invisible in rendered
#: markdown but searchable via the API.
COMMENT_MARKER = "<!-- kicad-bot:report -->"

_API_ROOT = "https://api.github.com"


class PRCommentError(RuntimeError):
    """Raised when the GitHub API interaction fails."""


def _github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def _repo() -> str | None:
    return os.environ.get("GITHUB_REPOSITORY")  # "owner/name"


def detect_pr_number(event_path: str | None = None) -> int | None:
    """Resolve the PR number from the Actions event payload, if any.

    Returns ``None`` when not running on a pull request (e.g. a push to main),
    in which case callers should skip commenting silently.
    """
    path = event_path or os.environ.get("GITHUB_EVENT_PATH")
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            event = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    pr = event.get("pull_request")
    if isinstance(pr, dict):
        num = pr.get("number")
        if isinstance(num, int):
            return num
    number = event.get("number")
    return number if isinstance(number, int) else None


def _request(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "kicad-bot")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
        return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise PRCommentError(f"GitHub API {method} {url} -> {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise PRCommentError(f"GitHub API request failed: {exc.reason}") from exc


def _find_existing_comment(repo: str, pr_number: int, token: str) -> int | None:
    page = 1
    while True:
        url = f"{_API_ROOT}/repos/{repo}/issues/{pr_number}/comments?per_page=100&page={page}"
        comments = _request("GET", url, token)
        if not comments:
            return None
        for comment in comments:
            if COMMENT_MARKER in (comment.get("body") or ""):
                return int(comment["id"])
        if len(comments) < 100:
            return None
        page += 1


def upsert_pr_comment(
    body: str,
    *,
    repo: str | None = None,
    pr_number: int | None = None,
    token: str | None = None,
) -> bool:
    """Create or update the kicad-bot PR comment.

    Returns ``True`` when a comment was created/updated, ``False`` when the call
    was skipped (not a PR, or no token) — skipping is not an error so local and
    push runs stay quiet.
    """
    token = token or _github_token()
    repo = repo or _repo()
    pr_number = pr_number if pr_number is not None else detect_pr_number()

    if not token:
        LOG.info("No GITHUB_TOKEN available; skipping PR comment.")
        return False
    if not repo:
        LOG.info("No GITHUB_REPOSITORY available; skipping PR comment.")
        return False
    if pr_number is None:
        LOG.info("Not running on a pull request; skipping PR comment.")
        return False

    if COMMENT_MARKER not in body:
        body = f"{COMMENT_MARKER}\n\n{body}"

    existing = _find_existing_comment(repo, pr_number, token)
    if existing is not None:
        _request(
            "PATCH",
            f"{_API_ROOT}/repos/{repo}/issues/comments/{existing}",
            token,
            {"body": body},
        )
        LOG.info("Updated existing PR comment %s.", existing)
    else:
        _request(
            "POST",
            f"{_API_ROOT}/repos/{repo}/issues/{pr_number}/comments",
            token,
            {"body": body},
        )
        LOG.info("Created PR comment on #%s.", pr_number)
    return True
