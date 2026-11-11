"""Check live public organisation repositories against the profile root links."""

import argparse
import json
import os
import re

# exception | file: tests/profile_repos.py | rule: B404 | category: D | entered: 2026-11-11 | expires: 2027-03-11 | reason: The bounded gh collector requires the standard subprocess module.
import subprocess  # nosec B404
import sys
import tempfile
import threading
import time
from typing import NamedTuple

from .repo_checks import (
    MAX_REPOSITORIES,
    REPOSITORY_FLAGS,
    ROOT,
    profile_repositories,
    unlisted_repositories,
)

MAX_API_OUTPUT = 1_000_000
MAX_API_STDERR = 4096
COLLECTION_CLEANUP_TIMEOUT = 5
REPOSITORY_KEYS = frozenset({"name", *REPOSITORY_FLAGS})
QUERY = ".[] | {name, archived, fork, private}"


class CollectionTimeout(Exception):
    """Report expiry of the shared output and child-exit collection deadline."""

    def __init__(self, timeout):
        """Retain the timeout while giving offline callers a useful message."""
        self.timeout = timeout
        super().__init__(f"gh collection timed out after {timeout} seconds")


class Collected(NamedTuple):
    """Immutable exit status and decoded output from a bounded child collection."""

    returncode: int
    stdout: str
    stderr: str


def _validate_repository(repository, line_number):
    """Refuse missing fields or invalid types with the response line number."""
    context = f"gh output line {line_number}"
    if not isinstance(repository, dict):
        raise TypeError(f"{context}: expected a JSON object")
    if not REPOSITORY_KEYS <= repository.keys():
        missing = sorted(REPOSITORY_KEYS - repository.keys())
        raise ValueError(f"{context}: missing repository key: {', '.join(missing)}")
    if not isinstance(repository["name"], str) or not repository["name"]:
        raise ValueError(f"{context}: name must be a non-empty string")
    if not all(isinstance(repository[key], bool) for key in REPOSITORY_FLAGS):
        raise ValueError(f"{context}: archived, fork and private must be booleans")


def _parse_repositories(stdout):
    """Parse bounded newline-delimited repository objects, refusing bad data."""
    if len(stdout) > MAX_API_OUTPUT:
        raise ValueError(f"gh output exceeds {MAX_API_OUTPUT} characters")
    repositories = []
    # Line count is bounded by MAX_API_OUTPUT, including blank lines.
    for line_number, line in enumerate(stdout.splitlines(), 1):
        if not line.strip():
            continue
        try:
            repository = json.loads(line)
        except ValueError as error:
            raise ValueError(f"gh output line {line_number}: malformed JSON: {error}") from error
        _validate_repository(repository, line_number)
        repositories.append(repository)
        if len(repositories) > MAX_REPOSITORIES:
            raise ValueError(f"gh output: more than {MAX_REPOSITORIES} repositories")
    return repositories


def _read_output(stream, limit, output, failures):
    """Read at most limit plus one bytes in a single bounded worker."""
    try:
        # Every nonempty read adds at least one byte, so limit + 1 bounds
        # iterations; the extra byte detects overflow without capturing more.
        for _ in range(limit + 1):
            chunk = stream.read(min(65536, limit + 1 - len(output)))
            if not chunk:
                return
            output.extend(chunk)
            if len(output) > limit:
                return
    except (OSError, ValueError) as error:
        failures.append(error)


def _stop_collection(process, reader):
    """Reap a live child and release its one reader with bounded cleanup."""
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=COLLECTION_CLEANUP_TIMEOUT)
    finally:
        if reader.ident is not None:
            reader.join(timeout=COLLECTION_CLEANUP_TIMEOUT)
        process.stdout.close()
    if reader.is_alive():
        raise ValueError("gh output reader did not stop after child termination")


def _collect_output(command, timeout, limit):
    """Collect bounded bytes portably under one deadline, then decode UTF-8."""
    deadline = time.monotonic() + timeout
    output, failures = bytearray(), []
    # Stderr writes to disk rather than a second pipe; read back only a prefix.
    with tempfile.TemporaryFile() as errors:
        # exception | file: tests/profile_repos.py | rule: B603, python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit | category: D | entered: 2026-11-11 | expires: 2027-03-11 | reason: The gh caller supplies fixed argv with a regex-validated owner and no shell.
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,  # nosec B603 # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit.dangerous-subprocess-use-audit
                                   stderr=errors, bufsize=0)
        # Fan-out bound: exactly one stdout reader, no additional workers.
        reader = threading.Thread(target=_read_output,
                                  args=(process.stdout, limit, output, failures), daemon=True)
        try:
            try:
                reader.start()
            except RuntimeError as error:
                raise ValueError(f"gh output reader could not start: {error}") from error
            reader.join(timeout=max(0, deadline - time.monotonic()))
            if reader.is_alive() or time.monotonic() >= deadline:
                raise CollectionTimeout(timeout)
            if failures:
                raise ValueError(f"gh output read failed: {failures[0]}") from failures[0]
            if len(output) > limit:
                raise ValueError(f"gh output exceeds {limit} bytes")
            try:
                returncode = process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as error:
                raise CollectionTimeout(timeout) from error
            errors.seek(0)
            try:
                stdout = output.decode("utf-8")
                stderr = errors.read(MAX_API_STDERR).decode("utf-8", errors="replace")
            except UnicodeDecodeError as error:
                raise ValueError(f"gh output is not valid UTF-8: {error}") from error
            if time.monotonic() >= deadline:
                raise CollectionTimeout(timeout)
            return Collected(returncode, stdout, stderr)
        finally:
            _stop_collection(process, reader)


def _fetch_repositories(owner):
    """Fetch all public repositories through gh with an explicit I/O deadline."""
    command = ["gh", "api", "--paginate", f"orgs/{owner}/repos?type=public&per_page=100", "--jq", QUERY]
    try:
        result = _collect_output(command, timeout=60, limit=MAX_API_OUTPUT)
    except FileNotFoundError as error:
        raise ValueError("gh executable not found") from error
    except CollectionTimeout as error:
        raise ValueError("gh api timed out after 60 seconds") from error
    if result.returncode:
        raise ValueError(f"gh api exited {result.returncode}: {result.stderr.strip()}")
    return _parse_repositories(result.stdout)


def main(argv=None) -> int:
    """Print missing profile links; return 0 for success, 1 for gaps, 2 for I/O."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "golusoris/.github"))
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", args.repository):
        print("profile repositories: repository must be OWNER/NAME", file=sys.stderr)
        return 2
    owner, self_name = args.repository.split("/")
    try:
        repositories = _fetch_repositories(owner)
        profile = (ROOT / "profile/README.md").read_text(encoding="utf-8")
        errors = unlisted_repositories(profile, owner, repositories, self_name)
    except (OSError, TypeError, ValueError) as error:
        print(f"profile repositories: {error}", file=sys.stderr)
        return 2
    for error in errors:  # Bounded by MAX_REPOSITORIES.
        print(error)
    if errors:
        return 1
    count = len(profile_repositories(repositories, self_name))
    print(f"profile/README.md: {count} public repositories linked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
