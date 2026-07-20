# AGENTS.md — house rules for this app

Read this first. This file tells an AI coding agent how **this specific app**
is built, what it may change freely, and — critically — how deploys work so a
change doesn't break the platform contract.

## Agent rules — read on entry

Every session starts by reading:

1. This file (`AGENTS.md`)
2. `docs/ai-tasks/context.md` — current focus / cross-task state
3. For any task you're about to work on, resume, or whose system you're
   about to touch: its files under `docs/ai-tasks/tasks/` — **the context
   file (`<NNN>-context-<name>.md`) first** when it exists.

### `docs/ai-tasks/` is the project's memory

The authoritative source of context — ahead of training data, assumptions,
and anything you think you remember. The scaffold ships the skeleton empty;
you fill it from the first session onward. Layout:

- `specs/` — approved designs (what/why per feature)
- `plans/` — implementation plans
- `tasks/{backlog,todo,in-progress,done}/` — the kanban board. One task =
  **paired files**:
  - `<NNN>-<kebab-name>.md` — summary: what / why / result, written so the
    **owner** can read it (plain language)
  - `<NNN>-context-<kebab-name>.md` — **build-ready context** for agents:
    concrete file paths, code snippets, exact commands, API/schema shapes,
    traps to avoid, acceptance checks, and an append-only decision log.
    Test: could a fresh session build the task from this file alone? If
    not, it's incomplete.
- `context.md` — focus ledger (`focus:` + `lastVerified:` frontmatter),
  updated at every milestone

Before acting: working on or resuming a task → read its context file first.
Touching an existing system → read the `done/` task that built it instead of
reverse-engineering. Making a decision that overlaps prior work → check the
decision log so you don't relitigate a settled call. Context that's missing
is a gap to **fill** in the files, not to guess around.

These files live under `docs/` but are deliberately NOT in the `mkdocs.yml`
nav — they're internal working state, not owner documentation.

### Task lifecycle

Status is the folder — `git mv` is the only state transition (never a
`status:` frontmatter field):

1. **backlog/** — captured ideas; summary file only is fine
2. **todo/** — committed to; summary + build-ready context both exist
   (context is written on this transition)
3. **in-progress/** — actively worked; keep the plan + decision log current
4. **done/** — fill the summary's Result section, `git mv` both files

Blocked → stays in `in-progress/` with the blocker noted in the context
file. Demoting is fine; keep the context file.

### Update discipline (load-bearing)

- **After every change, audit for staleness — proactively.** The doc set:
  this file, `README.md`, `docs/`, `docs/ai-tasks/`. If your change makes
  any of them inaccurate, fix them in the same commit. Stale docs are
  worse than missing docs.
- Non-obvious decisions go in the task's decision log — append-only;
  supersede, never edit past entries.
- Update `lastVerified:` when re-confirming a context file against
  current reality.
- Style for these files: terse, headers and lists, no emoji unless asked.

## What this is

A **FastAPI + React** app scaffolded on the **Nezam platform**. The React
frontend and FastAPI backend are built into **one Docker image**: FastAPI
serves the JSON API under `/api/*` and also serves the built React SPA at `/`.
The platform deploys that image to staging and production for you.

## Layout (the real repo)

```
backend/                 FastAPI app
  app/main.py            core routes + app-level error handlers + SPA fallback
  app/routers/           feature routers (APIRouter modules) — put routes HERE
  app/services/          business logic the routers call
  tests/                 pytest suite (real Postgres; see conftest.py contract)
  requirements.txt       pinned RUNTIME deps (ships in the image)
  requirements-dev.txt   test-only deps (pytest, httpx) — NEVER in the image
  entrypoint.sh          alembic upgrade head (retry + background self-heal), then uvicorn
  alembic/versions/      DB migrations (one example: 0001_create_app_meta.py)
frontend/                React + Vite SPA
  src/App.jsx            the demo page (hits /api/hello, /api/db-check, /api/version)
  src/__tests__/         Vitest tests (plain modules — see src/status.js)
  vite.config.js         dev server proxies /api + /healthz → :8080
Dockerfile               multi-stage: node build → python:3.12-slim runtime
deploy/                  GitOps manifests — PLATFORM-MANAGED (see below)
  base/                  Deployment (incl. your resource budget), Service, HTTPRoute
  staging/               staging overlay — image tag written by CI
  prod/                  prod overlay — image tag pinned by the release workflow
  preview/               ephemeral per-PR overlay (Flux-substituted vars)
.github/workflows/       ci.yaml (test → build → staging deploy) + release.yaml
catalog-info.yaml        Backstage/portal catalog entry
mkdocs.yml + docs/       TechDocs (portal Docs tab) — plain-language owner docs
docs/ai-tasks/           YOUR memory: specs, plans, task board (not in the docs nav)
scripts/
  dev.sh                 one-command local test loop (docker Postgres + venv + pytest)
  init.sh                one-time placeholder substitution (portal does it for you)
  release.sh             manual prod release fallback (prefer the release workflow)
```

## Current API routes (`backend/app/main.py`)

- `GET /api/hello` — static JSON greeting.
- `GET /api/db-check` — round-trips `SELECT now()` against Postgres; returns
  503 if the DB is unreachable (never leaks raw error text to the client).
- `GET /api/version` — reports `APP_VERSION` (baked into the image at build).
  **This is your deploy-verification signal** (see below).
- `GET /healthz` — readiness; deliberately DB-free.
- `GET /{full_path:path}` — SPA catch-all, registered **last** so every
  `/api/*` and `/healthz` route wins. New routes go in `app/routers/`
  modules, included from `main.py` **above** the catch-all.

`main.py` also installs app-level handlers that turn database errors
(unreachable DB, not-yet-applied migration) into a generic JSON 503 on every
endpoint — keep that behavior when you add routes; never let `/api/*` return
a text/plain 500 because the DB blipped.

## How deploys work — GET THIS RIGHT

Current mode (ADR-028 — deploy gate SUSPENDED; `main` is unprotected and CI
self-merges its own deploy PR):

1. Land changes on `main` **via a Pull Request** with CI green. The `test`
   job (pytest against real Postgres + Vitest + frontend build) gates the
   image build — a red test means nothing ships.
2. CI builds `ghcr.io/__USER__/__APP__:main-<shortsha>`, opens a staging
   deploy PR bumping `deploy/staging/kustomization.yaml`, and **merges it
   itself immediately** (squash, `[skip ci]` subject) — no human approval
   in the loop right now.
3. **Flux** applies it → live at **`https://__APP__-staging.nezam.site`**
   (~3–4 min after your merge).
4. **Verify every merge yourself**: poll `/api/version` until it equals
   `main-<your short sha>`. Don't declare success before it does.

**Production** ships only by a **semver git tag** (`vX.Y.Z`). Preferred:
the *Release to Production* workflow —
`gh workflow run release.yaml -f bump=patch|minor|major` (builds the image,
pins `deploy/prod/kustomization.yaml`, tags, creates the GitHub Release).
Manual fallback: `./scripts/release.sh X.Y.Z`. Flux tracks semver tags →
live at **`https://__APP__.nezam.site`**. Release only with the owner's
explicit go-ahead, after they've verified staging.

> **NEVER hand-edit the `newTag:` image tags in `deploy/staging/` or
> `deploy/prod/`.** CI owns the staging tag; the release workflow owns the
> prod tag. Editing them by hand fights the automation and breaks the deploy
> log (every deploy is supposed to be a CI/release commit).

### Deploy sharp edges (all observed live — recovery is one command)

- **GitHub sometimes drops push events.** If `/api/version` hasn't reached
  `main-<your sha>` in ~5 min, check `gh run list --branch main` — if no `ci`
  run exists for your merge sha, the push event was lost. Retrigger:
  `gh workflow run ci.yaml --ref main`.
- **Wait for checks to EXIST, not just not-fail.** During GitHub Actions
  lag, `gh pr checks --watch` can return "no checks reported" and let a
  merge sail through unchecked. Before merging, confirm the checks are
  actually listed (and green).
- **Never merge an old `deploy/staging-*` PR.** CI closes superseded deploy
  PRs automatically, but if you ever find one open that's older than the
  newest build, close it — merging it would roll staging BACK.

## Your runtime budget

The platform gives each container, per environment (numbers are explicit in
`deploy/base/deployment.yaml` so they're visible in-file):

- **Default:** 25m CPU / 64Mi memory requested, **128Mi memory limit**
  (no CPU limit).
- **Ceiling (tenant quota, per env):** 500m CPU + 512Mi memory in requests,
  1Gi in memory limits, 10 pods.

Raising `resources:` in `deploy/base/deployment.yaml` within that quota is
allowed and normal. But the limit is enforced by an OOM-kill, so:

- **Memory-hungry libraries must be tuned to fit** — password hashing
  (argon2id's library default is 64MiB *per hash*; two concurrent logins at
  defaults OOM-killed a real app on this platform), image processing,
  data-frame work. Prefer container-friendly parameters + a concurrency cap
  over just raising the limit.
- `pip install`-time dependency size is not the problem; **per-request
  memory spikes are** what kills pods.

## What you may change freely

- `backend/` — routers, services, new alembic migrations.
- `frontend/` — components, pages, styling.
- Tests — extend `backend/tests/` and `frontend/src/__tests__/` (see
  Conventions; the smoke tests that ship with the scaffold must stay green).
- `docs/` — the TechDocs pages (keep them plain-language for the owner) and
  `docs/ai-tasks/` (your working memory).

## Handle with care (the platform contract)

Change these only when the task genuinely requires it, and keep changes
minimal and reviewable:

- `deploy/**` layout and manifests — hostnames
  `<app>-staging.nezam.site` / `<app>.nezam.site`, service port **8080**,
  `/healthz` readiness — and **never** the `newTag:` values (see above).
  On the platform, the STAGING HTTPRoute is additionally rewritten at
  deploy time (KEDA scale-to-zero, platform ticket 033): its `rules` list
  is replaced wholesale to point at the interceptor — custom staging
  rules/filters in `deploy/base/httproute.yaml` will be overridden there
  (they still work when the repo is deployed standalone).
- `.github/workflows/ci.yaml` and `.github/workflows/release.yaml` — the
  build / staging-deploy / release / preview pipeline.
- `Dockerfile` — the single image is the deploy unit: it must keep serving
  HTTP on **8080** (frontend + `/api/*` + `/healthz`) and keep building.
- `catalog-info.yaml` annotations (`github.com/project-slug`,
  `backstage.io/techdocs-ref`, `backstage.io/kubernetes-id`,
  `nezam.space/template-repo`, `nezam.space/template-version`) — the portal
  and the template upgrade skill rely on them.

### Divergence warning — do this whenever a change touches the files above

These files are the PLATFORM CONTRACT: the platform builds, deploys, routes
and displays this app through them, and future template upgrades assume they
still broadly match the template. When the user asks for a change that
touches any of them:

1. **Warn in plain language**: this file is part of the platform deploy
   contract; changing it can break staging/prod deploys and will make future
   template upgrades harder (the upgrade skill has to merge around it).
2. **Offer a non-contract alternative** when one exists — most features need
   only `backend/`, `frontend/`, or `docs/`.
3. If it IS required: keep the change **minimal**, explain it in the PR body,
   and state the divergence explicitly ("diverges from template <version>:
   <what and why>").
4. **Offer an upgrade-compatibility review**: fetch the same file at the
   template's latest tag
   (`gh api "repos/nezam-org/template-fastapi-react/contents/<path>?ref=<tag>" --jq .content | base64 -d`)
   and tell the user whether their change conflicts with where the template
   is heading.

CI posts a non-blocking comment on any PR touching these paths (the
`contract-watch` job) — that net exists for direct human edits; you should
have warned before it fires.

## Preview environments — the database is SHARED with staging

Label a same-repo PR `preview` and the platform spins up an ephemeral copy at
`https://__APP__-pr-<n>.nezam.site` (cap: 2 concurrent; fork PRs
unsupported). Useful for showing UI work before merge. **But know this:**

> **Previews run against the STAGING database** (platform ADR-024 — per-PR
> databases don't exist yet). Migrations in a `preview`-labeled PR run
> against live staging data BEFORE the PR is merged, and every write a
> preview makes is visible in staging.

Therefore:

- **NEVER label a PR `preview` if it carries a migration** — you'd mutate
  the staging schema from an unmerged branch.
- Treat preview sessions as writing to staging (because they are). Don't
  run destructive flows from a preview.

## Template version & upgrades (the upgrade skill)

This app was scaffolded from a versioned platform template. The provenance
lives in `catalog-info.yaml`:

```yaml
metadata:
  annotations:
    nezam.space/template-repo: nezam-org/template-fastapi-react
    nezam.space/template-version: v1.2.0   # the tag this app came from
```

Template releases are git tags (`vX.Y.Z`) on the template repo. If the
annotations are missing, this app predates stamping: treat it as `v1.0.0`
and ADD both annotations in your next PR.

### How to upgrade this app to the latest template version

Run this when the user asks for an upgrade (or accepts your offer). Needs the
`gh` CLI authenticated as the repo owner.

1. **Current vs target.** Current = the `nezam.space/template-version`
   annotation (missing → `v1.0.0`). Target =
   `gh api repos/nezam-org/template-fastapi-react/tags --paginate --jq '.[].name' | sort -V | tail -1`
   (`--paginate`: the endpoint returns 30/page — unpaginated goes silently
   wrong past 30 releases).
   Equal → report "already up to date", stop. Upgrades are CUMULATIVE:
   go current → latest in ONE pass, never one release at a time.
2. **Fetch the delta.**
   `gh api "repos/nezam-org/template-fastapi-react/compare/<current>...<target>"`
   — `.files[]` carries `filename`, `status`, `patch`. If a `patch` is
   missing/truncated, read the whole file at the target:
   `gh api "repos/nezam-org/template-fastapi-react/contents/<path>?ref=<target>" --jq .content | base64 -d`.
3. **Translate template-speak.** The template's raw files use literal
   double-underscore placeholder tokens (USER, APP, TEMPLATE_VERSION wrapped
   in `__`) — this file can't spell them out, or scaffolding would substitute
   them here too. Map them before applying anything: the USER token → this
   repo's owner, the APP token → this repo's name, the TEMPLATE_VERSION
   token → the TARGET tag.
4. **Apply the delta as INTENT, file by file — never as a blind patch.**
   - File unchanged since scaffold → apply the change directly.
   - File diverged here → understand what the template change ACHIEVES and
     re-implement that intent in the current file. NEVER revert or overwrite
     user code to make a patch apply.
   - Skip entirely: the `VERSION` and `TEMPLATE.md` files (template-repo
     metadata — this app doesn't carry them) and any `newTag:` value changes
     in `deploy/*/kustomization.yaml` (deploy churn; CI owns those values
     here).
   - `catalog-info.yaml`: do NOT copy the template's file — set
     `nezam.space/template-version` to the target tag (add
     `nezam.space/template-repo` if missing) and merge only genuinely NEW
     annotations/links the delta introduces.
   - `AGENTS.md` (this file) is template content too — apply its changes as
     well; updated instructions take effect next session.
5. **Open a PR** — branch `template-upgrade/<target>`, never push `main`.
   Title: `chore: upgrade to template <target>`. Body: a plain-language list
   of every template change and how you handled it (applied / adapted to a
   divergence / skipped + why), so the owner can judge it without reading
   diffs.
6. **The gate: CI must be green on the PR.** Red → fix INSIDE the PR by
   adapting your application of the delta; never weaken the app's tests or CI
   to get to green; never merge red.
7. **Merge** (squash) once green. If branch protection blocks you, hand the
   merge to the owner — force nothing.
8. **Verify**: the annotation now reads `<target>`; staging deploys as usual
   after the merge.

## Conventions

- **FastAPI routes** go in `APIRouter` modules under `backend/app/routers/`,
  included from `app/main.py` **above** the SPA catch-all. Business logic
  the routes call goes in `backend/app/services/`. Keep `/api/*` prefixes
  for JSON endpoints. Don't grow `main.py` into a single-file app.
- **DB schema changes** are alembic migrations:
  `cd backend && alembic revision -m "add my_table"` — a new file lands in
  `backend/alembic/versions/` next to `0001_create_app_meta.py`. Migrations
  run automatically on container start; keep them idempotent-safe.
- **React components** go in `frontend/src/`. `App.jsx` is demo scaffolding —
  replace it freely. Logic you want tested goes in plain modules (like
  `src/status.js`) with tests in `src/__tests__/`.
- **Keep the single Dockerfile building** — the frontend build stage and the
  python runtime stage must both stay green.
- **Small, reviewable PRs.** One change per PR; explain it in plain language
  in the PR body so the owner (who may not read code) can approve with
  confidence.
- **Prove config at write time.** Any endpoint that stores configuration
  consumed later by a background job must prove it works in the same request
  (one live probe → friendly 400 on failure) or expose `last_run_at` /
  `last_error` in the API. Never save config the runtime hasn't demonstrated
  it can use — "saved but silently dead" features are a whole failure class.
- **Adversarial review before merging a non-trivial PR.** While CI runs, do
  a light find-then-try-to-refute pass focused on concurrency, external-API
  assumptions (redirects, timeouts, shape changes), and permission gaps. Fix
  confirmed findings in the same PR. On a real app this caught double-digit
  pre-merge bugs at 10–20 minutes per PR.

## Security checklist (when you add auth or handle user input)

Building auth from scratch is where subtle bugs live. Every item below is a
bug class that was actually caught on this platform:

- **argon2id tuned for the container** — use an OWASP low-memory profile
  (e.g. `m=19456 KiB, t=2, p=1`) plus a small concurrency cap, never library
  defaults (64MiB per hash × concurrent requests = OOM at the 128Mi limit).
- **Rate-limit on the RIGHTMOST `X-Forwarded-For` entry** — the gateway
  appends the real client IP last; the leftmost entries are
  client-spoofable.
- **No login timing oracle** — when the username doesn't exist, verify a
  dummy hash anyway so "user exists" and "wrong password" take the same
  time.
- **Commit before responding** — never leave DB work to run after the
  response is sent (phantom writes that vanish on error).
- **Enforce session expiry server-side** — a rolling expiry must be checked
  and refreshed in the DB, not just via cookie `max-age`.
- **Origin-check middleware for state-changing requests** — with
  `SameSite=Lax` cookies, rejecting mismatched `Origin` headers on
  POST/PATCH/PUT/DELETE blocks cross-site form posts.
- **Never leak raw errors** — the shipped JSON-503 handler pattern: generic
  client bodies, full tracebacks only in server logs.

## Secrets & config

- **Never commit secrets.** No credentials, tokens, or connection strings in
  the repo — not even in `docs/ai-tasks/` context files.
- Database credentials arrive as **environment variables injected by the
  platform** from the `app-db` Secret: `DB_HOST`, `DB_PORT`, `DB_NAME`,
  `DB_USER`, `DB_PASSWORD`. `APP_VERSION` is baked into the image at build
  time.
- **Need a NEW secret (API key, VAPID keys, …)?** There is no self-service
  yet — the **platform owner** must add it (it's stored encrypted in the
  platform repo and lands as a Kubernetes Secret in this app's namespaces).
  The flow that works:
  1. Wire the env var now with `optional: true`, so the app boots before
     the secret exists and picks it up on the next restart after it lands:
     ```yaml
     - name: MY_API_KEY
       valueFrom:
         secretKeyRef: { name: app-secrets, key: my-api-key, optional: true }
     ```
     In code, read it with a safe local default and degrade gracefully
     (feature off + clear log line) when it's unset.
  2. Ask the owner to request the secret from the platform (key name +
     value over a private channel — **never** through git, a PR body, or an
     issue).
- Non-secret config: env var with a safe local default, set via
  `deploy/base/deployment.yaml`.

## Local dev + tests

**The one command** (starts a docker test Postgres, makes a venv, installs
dev deps, runs pytest — extra args pass through to pytest):

```sh
./scripts/dev.sh            # backend tests
./scripts/dev.sh --all      # + frontend tests + production build
```

Test infrastructure contract (already wired — don't reinvent it):

- `backend/tests/conftest.py` expects Postgres with **user `app` / password
  `test` / db `app_test`** on `localhost:5433` (override:
  `TEST_DB_HOST`/`TEST_DB_PORT`). It applies all alembic migrations once per
  session and truncates app tables between tests.
- CI's `test` job runs the same suite against a Postgres **18** service
  container (same major as the platform's shared cluster) and gates the
  image build — you don't need to wire anything for new tests to count.
- **Test deps go in `backend/requirements-dev.txt`**, runtime deps in
  `backend/requirements.txt`. Never add pytest/httpx to `requirements.txt` —
  it ships them into the production image.
- Frontend tests are Vitest (`cd frontend && npm run test`), colocated in
  `src/__tests__/`.

Run the app itself locally:

```sh
# Backend (terminal 1). /api/db-check returns 503 without a local Postgres — fine.
cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8080

# Frontend (terminal 2). Dev server on :5173, proxies /api → :8080.
cd frontend && npm install && npm run dev
```

Or build the real image the way the platform does:

```sh
docker build -t __APP__ . && docker run -p 8080:8080 __APP__
```

## Developing with AI (the loop, for you the agent)

The owner may not be a developer. Work like this:

1. Take their plain-English description of the change; capture it as a task
   in `docs/ai-tasks/tasks/` (summary + context file).
2. Read **this file** for the guardrails, then make the change in `backend/`,
   `frontend/`, or `docs/`. Add/extend tests for what you changed.
3. Open a **Pull Request** (never push to `main` directly). Explain the change
   in plain language in the PR body so the owner can approve confidently. Run
   the adversarial review pass while CI runs; fix findings in the same PR.
4. After merge, staging deploys **automatically** (ADR-028 — gate
   suspended); verify `/api/version` == `main-<sha>` on
   `https://__APP__-staging.nezam.site` (see "Deploy sharp edges" if it
   doesn't arrive), then tell the owner it's ready to try.
5. When they're happy on staging and say so, release with
   `gh workflow run release.yaml -f bump=patch|minor|major` to ship to
   `https://__APP__.nezam.site`.
6. Move the task to `done/`, fill in its Result, and update
   `docs/ai-tasks/context.md` — the files, not the chat, are what persists.

Keep the owner in control: **nothing reaches production without their
approval**, and you never edit deploy image tags by hand.
