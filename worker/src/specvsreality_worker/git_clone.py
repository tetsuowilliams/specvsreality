"""Helpers for cloning tracked repositories."""

from __future__ import annotations

from urllib.parse import quote, urlsplit, urlunsplit

from git.exc import GitCommandError

from specvsreality_worker.config import WorkerSettings

_AUTH_FAILURE_MARKERS = (
    "authentication failed",
    "could not read username",
    "401",
    "403",
    "invalid credentials",
    "repository not found",
    "not found",
)


def clone_url_with_optional_token(raw_url: str, settings: WorkerSettings) -> str:
    parsed = urlsplit(raw_url)
    if parsed.scheme != "https":
        return raw_url
    if parsed.username is not None:
        return raw_url

    token = settings.git_clone_token.strip()
    if not token:
        return raw_url

    username = settings.git_clone_username.strip() or "x-access-token"
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port is not None else ""
    netloc = f"{quote(username)}:{quote(token, safe='')}@{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _git_command_detail(exc: GitCommandError) -> str:
    if exc.stderr:
        return exc.stderr.strip()
    if exc.stdout:
        return exc.stdout.strip()
    return str(exc).strip()


def _exception_detail(exc: BaseException) -> str:
    if isinstance(exc, GitCommandError):
        return _git_command_detail(exc)
    parts = [str(exc).strip()]
    cause = exc.__cause__
    while cause is not None:
        if isinstance(cause, GitCommandError):
            parts.append(_git_command_detail(cause))
        else:
            parts.append(str(cause).strip())
        cause = cause.__cause__
    return "\n".join(part for part in parts if part)


def _needs_auth_hint(detail: str) -> bool:
    lowered = detail.lower()
    return any(marker in lowered for marker in _AUTH_FAILURE_MARKERS)


def format_init_repo_error(
    *,
    repo_id: int,
    url: str,
    exc: BaseException,
    max_len: int = 16_384,
) -> str:
    """Build a persisted init failure message with as much git output as possible."""
    detail = _exception_detail(exc)
    lines = [f"Failed to initialize repository (id={repo_id}, url={url!r})."]
    if detail:
        lines.append(detail)
    if _needs_auth_hint(detail):
        lines.append("If this repository is private, set GIT_CLONE_TOKEN.")
    message = "\n".join(lines)
    if len(message) <= max_len:
        return message
    return message[: max_len - 3] + "..."
