"""Print the shared rendered-Markdown manifest for the external link checker."""

import sys

from .repo_checks import MAX_MARKDOWN_FILES, ROOT, markdown_files


def main() -> int:
    """Print repository-relative POSIX paths, or report a discovery error."""
    try:
        for path in markdown_files()[:MAX_MARKDOWN_FILES]:
            print(path.relative_to(ROOT).as_posix())
    except (OSError, ValueError) as error:
        print(f"Cannot list Markdown files: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
