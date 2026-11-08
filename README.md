# golusoris/.github

[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/16160/badge)](https://www.bestpractices.dev/projects/16160)

Organisation-wide community health files and the public organisation profile
for [golusoris](https://github.com/golusoris). The profile page itself lives in
[`profile/README.md`](profile/README.md).

Local checks: `make verify-all` runs the full gate; `make audit` and
`make compile-context-verify` run its parts. The Makefile uses `praetorctl` or
`standardsctl`, whichever is installed.

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
