# Contributing

This file covers every golusoris repository that ships no `CONTRIBUTING.md` of its own.

## Review

golusoris has a single maintainer. Pull requests merge once the required checks pass and need no approving review; the `praetor-main-protection` ruleset requires zero approvals, signed commits and linear history. This holds until a second maintainer joins.

Review bots, such as CodeRabbit, Sourcery and Codacy, comment on pull requests. Each comment is fixed or answered, and each review thread is resolved, before the pull request merges: the ruleset blocks merging while a review thread is unresolved. A top-level comment, such as a bot's walkthrough, has no thread to resolve. No bot review counts as an approval.

## Commits

Commits are signed and carry a `Signed-off-by` trailer (`git commit -s -S`). Pull request titles follow [Conventional Commits](https://www.conventionalcommits.org/).

## Security issues

Report vulnerabilities as described in [SECURITY.md](SECURITY.md), never in a public issue.
