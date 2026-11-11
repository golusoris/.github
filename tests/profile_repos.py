"""Check live public organisation repositories against the profile root links."""

import argparse
import json
import os
import re
import subprocess
import sys

from .repo_checks import (
    MAX_REPOSITORIES,
    REPOSITORY_FLAGS,
    ROOT,
    profile_repositories,
    unlisted_repositories,
)

MAX_API_OUTPUT = 1_000_000
REPOSITORY_KEYS = frozenset({"name", *REPOSITORY_FLAGS})
QUERY = ".[] | {name, archived, fork, private}"


def _validate_repository(repository, line_number):
    """Refuse missing fields or invalid types with the response line number."""
    context = f"gh output line {line_number}"
    if not isinstance(repository, dict):
        raise ValueError(f"{context}: expected a JSON object")
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


def _fetch_repositories(owner):
    """Fetch all public repositories through gh with an explicit I/O deadline."""
    command = ["gh", "api", "--paginate", f"orgs/{owner}/repos?type=public&per_page=100", "--jq", QUERY]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    except FileNotFoundError as error:
        raise ValueError("gh executable not found") from error
    except subprocess.TimeoutExpired as error:
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
    except (OSError, ValueError) as error:
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
