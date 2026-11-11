# golusoris/.github

<!-- markdownlint-disable MD013 -->
<!-- 2 CI/build -->
[![Tests](https://img.shields.io/github/actions/workflow/status/golusoris/.github/test.yml?branch=main&event=push&style=for-the-badge&label=Tests&labelColor=111a35)](https://github.com/golusoris/.github/actions/workflows/test.yml)
[![REUSE](https://img.shields.io/github/actions/workflow/status/golusoris/.github/reuse.yml?branch=main&event=push&style=for-the-badge&label=REUSE&labelColor=111a35)](https://github.com/golusoris/.github/actions/workflows/reuse.yml)
<!-- 3 security/scorecard -->
[![OpenSSF Scorecard](https://img.shields.io/ossf-scorecard/github.com/golusoris/.github?style=for-the-badge&label=OpenSSF%20Scorecard&labelColor=111a35)](https://scorecard.dev/viewer/?uri=github.com/golusoris/.github) [![OpenSSF Best Practices](https://www.bestpractices.dev/projects/16160/badge)](https://www.bestpractices.dev/projects/16160)
<!-- 4 standards -->
[![Conventional Commits](https://img.shields.io/badge/Commits-Conventional-8b5cf6?style=for-the-badge&logo=conventionalcommits&logoColor=white&labelColor=111a35)](CONTRIBUTING.md)
<!-- 5 licence -->
[![License](https://img.shields.io/badge/License-EUPL--1.2_·_CC--BY--SA--4.0-3b82f6?style=for-the-badge&labelColor=111a35)](REUSE.toml)
<!-- markdownlint-enable MD013 -->

**Community health files and the public profile of the golusoris organisation.**

Organisation-wide community health files and the public organisation profile
for [golusoris](https://github.com/golusoris). The profile page itself lives in
[`profile/README.md`](profile/README.md).

Local checks: `make verify-all` runs the full gate; `make audit` and
`make compile-context-verify` run its parts. The Makefile uses `praetorctl` or
`standardsctl`, whichever is installed.

## Tests

`make test` runs the suite under [`tests/`](tests/) with Python's `unittest`.
It needs Python 3.10 or later, PyYAML and markdown-it-py, pinned with hashes in
[`.config/tests/requirements.txt`](.config/tests/requirements.txt). The
[Tests workflow](.github/workflows/test.yml) runs it on every pull request, on
`main` and in the merge queue.

The suite checks what this repository publishes to the organisation:

- [`labels.yml`](labels.yml) has the shape EndBug/label-sync reads, a
  six-digit colour on every label, and no name or alias twice
  ([`tests/test_labels.py`](tests/test_labels.py)).
- [`.bestpractices.json`](.bestpractices.json) gives every criterion a valid
  status and a justification
  ([`tests/test_bestpractices.py`](tests/test_bestpractices.py)).
- Every relative link in the profile, the community health files and the
  decision records names a file that exists
  ([`tests/test_markdown_links.py`](tests/test_markdown_links.py)).
- Banner text keeps at least 24 units of clearance from the wave paths
  ([`tests/test_banner.py`](tests/test_banner.py)).
- The profile links every public, unarchived, non-fork organisation repository
  except `.github` ([`tests/test_profile_repos.py`](tests/test_profile_repos.py)).
  `make profile-repos` checks the live repository list through `gh`; the
  [Profile workflow](.github/workflows/profile.yml) runs it on pull requests
  that touch the profile or the checks, on `main` and weekly, so new public
  repositories are detected even without a push here.
- Every `.lycheeignore` pattern carries a dated exception that has not
  expired and still matches a link
  ([`tests/test_link_exceptions.py`](tests/test_link_exceptions.py)).

The [Links workflow](.github/workflows/links.yml) checks external links with
lychee on pull requests that touch Markdown or the link check, on `main` and
weekly.

Test policy: a change that adds a published file, or a rule for one, adds a
test to `tests/` in the same pull request, with a passing case, a refused
planted defect and the boundary between them. A fix adds a test that fails
without it.

<!-- praetor:readme-governance:start -->
[![HISS Adopted][praetor-hiss-badge]][praetor-hiss-agents]

Praetor manages this repository's declared governance policy. This managed
block records adoption state; it is not a verification certificate.

**Verification**: `make verify-all` runs the repository's configured
verification cascade.

**HISS Audit**: `praetorctl audit` enforces policy, generated-surface
integrity, and the debt ratchet.

**Context Sync**: `praetorctl compile-context --verify` verifies every
generated agent context against `AGENTS.md`.

**Debt Baseline**: `.standards-baseline.json` anchors the debt ratchet at
1 recorded infraction; audit forbids growth.

[praetor-hiss-badge]: https://img.shields.io/badge/Standards-HISS%20Adopted%20(1%20baselined)-yellow
[praetor-hiss-agents]: https://github.com/golusoris/.github/blob/HEAD/AGENTS.md
<!-- praetor:readme-governance:end -->
