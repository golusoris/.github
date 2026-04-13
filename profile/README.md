# golusoris

A composable Go framework — opt-in `fx` modules for everything a production backend needs.

```go
import "github.com/golusoris/golusoris"

fx.New(
    golusoris.Core,            // config + log + clock + id + validate + crypto
    golusoris.DB,              // pgx pool + migrations + sqlc helpers
    golusoris.HTTP,            // server + middleware + Scalar API docs
    golusoris.OTel,            // tracer + meter + logs + OTLP
    golusoris.Auth.OIDC,
    golusoris.Jobs,            // river queue
    golusoris.Cache.Memory,
    golusoris.K8s.Health,      // /livez /readyz /startupz
    // ... pick what you need
).Run()
```

## Repositories

- **[golusoris/golusoris](https://github.com/golusoris/golusoris)** — the framework
- **[golusoris/goenvoy](https://github.com/golusoris/goenvoy)** — typed clients for arr-stack, TMDB, AniList, Trakt, etc.

## Apps built on golusoris

- [lusoris/revenge](https://github.com/lusoris/revenge), [lusoris/lurkarr](https://github.com/lusoris/lurkarr), [lusoris/subdo](https://github.com/lusoris/subdo), [lusoris/arca](https://github.com/lusoris/arca)

## Funding

If golusoris saves you time, consider supporting on [Ko-fi ☕](https://ko-fi.com/lusoris) or [GitHub Sponsors](https://github.com/sponsors/lusoris).
