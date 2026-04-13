# golusoris

Foundational Go libraries + the apps built on top of them.

## What's here

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
|---|---|---|
| none | library | `golusoris/goenvoy` |
| `app-` | application consuming the framework | `golusoris/app-revenge` |
| `cmd-` | standalone CLI (future) | `golusoris/cmd-…` |

The namesake repo `golusoris/golusoris` is the framework itself.

## Support

<p align="left">
  <a href="https://ko-fi.com/lusoris" target="_blank">
    <img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support me on Ko-fi" />
  </a>
  &nbsp;&nbsp;
  <a href="https://github.com/sponsors/lusoris" target="_blank">
    <img src="https://img.shields.io/badge/Sponsor-%E2%9D%A4-ea4aaa?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Sponsors" />
  </a>
</p>
