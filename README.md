# template-fastapi-react

Batteries-included app template for the nezam platform: React (Vite) frontend
+ FastAPI backend, shipped as **one image**, deployed by Flux to
`https://<app>-staging.nezam.site` and `https://<app>.nezam.site`.

## Start here

1. Click **"Use this template"** on GitHub (or plain clone-and-copy — nothing
   here is GitHub-specific except the CI workflow).
2. From your new repo's root:

   ```sh
   ./scripts/init.sh <your-github-user> <app-name>   # lowercase alnum/dash
   git push
   ```

3. Ask the platform to register the app (namespaces, Flux sync, DB role — see
   the platform runbook *"Register a tenant app"*).
4. After CI's first push, make the `ghcr.io/<user>/<app>` package **public**
   (GitHub → your profile → Packages → package settings → Change visibility).
   One-time step.

## How your app ships

### Staging: merge to main (~1 minute)

Every push to `main`:

1. CI builds the image and pushes `ghcr.io/<user>/<app>:main-<shortsha>`.
2. CI commits that tag into `deploy/staging/kustomization.yaml`
   (`[skip ci] deploy: staging → main-<shortsha>`).
3. Flux (watching `main`) applies it — staging serves your build about a
   minute after CI finishes.

Every staging deploy is a git commit: the history of
`deploy/staging/kustomization.yaml` **is** your deploy log, and rollback is
`git revert`.

### Prod: cut a release

```sh
./scripts/release.sh 1.2.3
```

This pins `deploy/prod` to `1.2.3`, commits, tags `v1.2.3`, and pushes. Flux
tracks semver tags (highest wins), so the tag push is the prod deploy;
rollback = tag a higher version from an older commit.

> **Expected blip:** Flux may apply the tagged commit ~1 minute before CI
> finishes pushing the image. Prod briefly shows `ImagePullBackOff`, then
> self-heals — no action needed.

## Database

The platform provides a Postgres database per environment and injects
credentials via the `app-db` Secret, surfaced to your code as env vars:
`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.

Migrations are alembic, run automatically on every container start
(`alembic upgrade head` in `backend/entrypoint.sh` — idempotent; retries,
then starts the server anyway with a loud log warning so a brief DB outage
never turns into a crashloop). Add schema:

```sh
cd backend && alembic revision -m "add my_table"
```

## What's where

| Path | What |
|---|---|
| `frontend/` | Vite + React SPA (one demo page hitting the API) |
| `backend/` | FastAPI: `/api/hello`, `/api/db-check`, `/api/version`, `/healthz`; serves the built SPA at `/` |
| `deploy/` | kustomize base + staging/prod overlays (Deployment, Service, HTTPRoute) |
| `Dockerfile` | multi-stage: node build → python:3.12-slim runtime |
| `.github/workflows/ci.yaml` | build+push image; staging writeback on main; release build on `v*` tags |
| `scripts/release.sh` | cut a prod release |
| `scripts/init.sh` | one-time placeholder substitution |
| `catalog-info.yaml` | Backstage/portal catalog stub |

The app version shown at `/api/version` is baked into the image at build time
(`--build-arg VERSION=...` → `APP_VERSION`); local builds report `dev`.

## Local development

```sh
# backend (terminal 1) — /api/db-check 503s without a local postgres; fine
cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8080

# frontend (terminal 2) — dev server proxies /api → :8080
cd frontend && npm install && npm run dev
```

Or the real thing: `docker build -t myapp . && docker run -p 8080:8080 myapp`.
