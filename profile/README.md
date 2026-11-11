<!-- markdownlint-disable MD013 MD023 MD033 MD036 MD041 -->
<!-- A centred header needs inline HTML, a banner image, indented headings and
     badge lines past 80 columns, so those five rules are off for this file.
     Same directive style as docs/adr/0000-template.md. The prose below still
     wraps at 80. -->
<div align="center">

  <img src="golusoris-readme-banner.svg" alt="golusoris — foundational Go libraries and applications" height="120" />

  <!-- README-STANDARD badge block: one group, fixed order (docs/README-STANDARD.md) -->
  <!-- 2 CI/build -->
  [![REUSE](https://github.com/golusoris/.github/actions/workflows/reuse.yml/badge.svg?branch=main&event=push)](https://github.com/golusoris/.github/actions/workflows/reuse.yml)
  <!-- 3 security/scorecard -->
  [![OpenSSF Scorecard](https://img.shields.io/badge/OpenSSF-Scorecard-06b6d4?style=for-the-badge&labelColor=111a35)](https://scorecard.dev/viewer/?uri=github.com/golusoris/.github)
  [![OpenSSF Best Practices](https://www.bestpractices.dev/projects/16160/badge)](https://www.bestpractices.dev/projects/16160)
  [![Codacy](https://app.codacy.com/project/badge/Grade/616e991478d846b6a826f536d9645dd2)](https://app.codacy.com/gh/golusoris/.github/dashboard)
  [![CodeRabbit](https://img.shields.io/badge/Reviews-CodeRabbit-8b5cf6?style=for-the-badge&logo=coderabbit&logoColor=white&labelColor=111a35)](https://coderabbit.ai)
  <!-- 4 standards -->
  [![HISS-21](https://img.shields.io/badge/Standards-HISS--21-06b6d4?style=for-the-badge&logo=nasa&labelColor=111a35)](https://github.com/golusoris/.github/blob/main/AGENTS.md)
  [![Conventional Commits](https://img.shields.io/badge/Commits-Conventional-8b5cf6?style=for-the-badge&logo=conventionalcommits&logoColor=white&labelColor=111a35)](https://github.com/golusoris/.github/blob/main/CONTRIBUTING.md)
  <!-- 5 licence -->
  [![License](https://img.shields.io/badge/License-EUPL--1.2_·_CC--BY--SA--4.0-3b82f6?style=for-the-badge&labelColor=111a35)](https://github.com/golusoris/.github/blob/main/profile/README.md#upstream-and-licence)
  <!-- 6 support -->
  [![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-8b5cf6?style=for-the-badge&logo=githubsponsors&logoColor=white&labelColor=111a35)](https://github.com/sponsors/lusoris)
  [![Ko-fi](https://img.shields.io/badge/Support-Ko--fi-8b5cf6?style=for-the-badge&logo=kofi&logoColor=white&labelColor=111a35)](https://ko-fi.com/lusoris)

  **Foundational libraries, frameworks, templates and applications**

  *The central [framework modules](https://github.com/golusoris/golusoris), [service clients](https://github.com/golusoris/goenvoy), and self-hosted apps of the golusoris ecosystem*

</div>

golusoris provides foundational libraries, frameworks and templates, and the
applications built on top of them. It encompasses [composable Go framework
modules covering core backend infrastructure](https://github.com/golusoris/golusoris)
using Uber's [`fx`](https://github.com/uber-go/fx) dependency-injection framework,
[zero-dependency typed clients for media automation and metadata
services](https://github.com/golusoris/goenvoy), a [composable SvelteKit
framework](https://github.com/golusoris/sveltesentio), a [repository template
for native C/C++ and GPU projects](https://github.com/golusoris/template-native-gpu),
and self-hosted applications listed under Apps.

---

## At a glance

### Libraries

- **[golusoris/golusoris](https://github.com/golusoris/golusoris)** — the framework: composable `fx` modules covering config, logging, errors, database, HTTP, OTel, jobs, cache, auth, k8s runtime, notifications, storage, AI, and more.
- **[golusoris/goenvoy](https://github.com/golusoris/goenvoy)** — typed clients for the *arr stack, metadata services (TMDB, AniList, Trakt, …), and download/indexer APIs. 60+ zero-dependency modules.
- **[golusoris/sveltesentio](https://github.com/golusoris/sveltesentio)** — composable SvelteKit framework with opt-in modules, Svelte 5 runes, and production-grade foundations.

### Templates

- **[golusoris/template-native-gpu](https://github.com/golusoris/template-native-gpu)** — polyglot native C/C++ and GPU project template with Meson, SYCL/CUDA/HIP/Metal/Vulkan dispatch, FFmpeg filters, and supply-chain CI (SLSA, cosign, SBOM). BSD-2-Clause-Patent.

This is a GitHub repository template; select **Use this template** to start a
project from it.

### Apps

All apps are built on the `golusoris` framework. Their repositories are not
published yet; each will use the `app-` prefix here:

- **app-revenge** — high-performance Go media server
- **app-lurkarr** — automated media hunting for *arr apps
- **app-subdo** — visual flow editor for media processing automation
- **app-arca** — self-hosted ROM management platform

## Naming convention

| Prefix | Kind | Example |
| --- | --- | --- |
| none | library | `golusoris/goenvoy` |
| `template-` | repository template | `golusoris/template-native-gpu` |
| `app-` | application consuming the framework | `golusoris/app-revenge` |
| `cmd-` | standalone CLI (future) | `golusoris/cmd-…` |

The namesake repo `golusoris/golusoris` is the framework itself.

## Contribute

Start with [CONTRIBUTING.md](https://github.com/golusoris/.github/blob/main/CONTRIBUTING.md)
for contribution guidelines, signing expectations, and Conventional Commits conventions.
Report vulnerabilities privately as described in [SECURITY.md](https://github.com/golusoris/.github/blob/main/SECURITY.md).

## Support

golusoris is free and open source. Support ongoing development, maintenance, and
infrastructure costs:

- **[GitHub Sponsors](https://github.com/sponsors/lusoris)** (sponsors/lusoris)
- **[Ko-fi](https://ko-fi.com/lusoris)** (lusoris)

## Upstream and licence

Code and workflows in this repository are licensed under the European Union Public
Licence v. 1.2 ([`EUPL-1.2`](https://github.com/golusoris/.github/blob/main/LICENSE)).
Markdown prose and documentation files are licensed under Creative Commons
Attribution-ShareAlike 4.0 International ([`CC-BY-SA-4.0`](https://github.com/golusoris/.github/blob/main/LICENSES/CC-BY-SA-4.0.txt))
per [`REUSE.toml`](https://github.com/golusoris/.github/blob/main/REUSE.toml).

## Standards & Governance

The `golusoris/.github` repository declares the 21 invariants of the
High-Integrity Systems Standard (HISS) from
[Praetor](https://github.com/cordanaLLM/praetor) in
[`AGENTS.md`](https://github.com/golusoris/.github/blob/main/AGENTS.md). Its
table names the check that enforces each invariant and marks the invariants
that are advisory only. Pull request titles follow Conventional Commits. Every
commit carries a cryptographic signature (`git commit -S`) and, separately, a
`Signed-off-by` trailer (`git commit -s`), as
[`CONTRIBUTING.md`](https://github.com/golusoris/.github/blob/main/CONTRIBUTING.md)
describes.
