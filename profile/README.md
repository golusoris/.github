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
  <!-- 4 standards -->
  [![HISS-21](https://img.shields.io/badge/Standards-HISS--21-06b6d4?style=for-the-badge&logo=nasa&labelColor=111a35)](https://github.com/golusoris/.github/blob/main/AGENTS.md)
  [![Conventional Commits](https://img.shields.io/badge/Commits-Conventional-8b5cf6?style=for-the-badge&logo=conventionalcommits&logoColor=white&labelColor=111a35)](https://github.com/golusoris/.github/blob/main/CONTRIBUTING.md)
  <!-- 5 licence -->
  [![License](https://img.shields.io/badge/License-EUPL--1.2_·_CC--BY--SA--4.0-3b82f6?style=for-the-badge&labelColor=111a35)](https://github.com/golusoris/.github/blob/main/LICENSE)
  <!-- 6 support -->
  [![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-8b5cf6?style=for-the-badge&logo=githubsponsors&logoColor=white&labelColor=111a35)](https://github.com/sponsors/lusoris)
  [![Ko-fi](https://img.shields.io/badge/Support-Ko--fi-8b5cf6?style=for-the-badge&logo=kofi&logoColor=white&labelColor=111a35)](https://ko-fi.com/lusoris)

  **Foundational Go libraries and the applications built on top of them**

  *The central framework modules, service clients, and self-hosted apps of the golusoris ecosystem*

</div>

golusoris provides foundational Go libraries and the suite of applications built
on top of them. It encompasses composable `fx` framework modules covering core
backend infrastructure, zero-dependency typed clients for media automation and
metadata services, and production self-hosted applications.

---

## At a glance

### Libraries

- **[golusoris/golusoris](https://github.com/golusoris/golusoris)** — the framework: composable `fx` modules covering config, logging, errors, database, HTTP, OTel, jobs, cache, auth, k8s runtime, notifications, storage, AI, and more.
- **[golusoris/goenvoy](https://github.com/golusoris/goenvoy)** — typed clients for the *arr stack, metadata services (TMDB, AniList, Trakt, …), and download/indexer APIs. 60+ zero-dependency modules.

### Apps

All apps are built on the `golusoris` framework and live here with the `app-` prefix:

- **[app-revenge](https://github.com/golusoris/app-revenge)** — high-performance Go media server
- **[app-lurkarr](https://github.com/golusoris/app-lurkarr)** — automated media hunting for *arr apps
- **[app-subdo](https://github.com/golusoris/app-subdo)** — visual flow editor for media processing automation
- **[app-arca](https://github.com/golusoris/app-arca)** — self-hosted ROM management platform

## Naming convention

| Prefix | Kind | Example |
| --- | --- | --- |
| none | library | `golusoris/goenvoy` |
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

This repository conforms to High-Integrity Systems Standards (HISS-21)
and Conventional Commits conventions.
