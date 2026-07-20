# __APP__

**__APP__** is your app, running on the Nezam platform. This page is for
you, the owner — you don't need to be a developer to build it, change it,
and ship it.

> Fresh copy of the template? One-time setup lives at the
> [bottom of this page](#first-time-setup-manual-copies-only). Apps created
> through the platform portal are already set up.

## Your app's two addresses

| | URL | What it's for |
|---|---|---|
| **Staging** | <https://__APP__-staging.nezam.site> | Every change lands here first, automatically. Look at it, click around, break things safely. |
| **Production** | <https://__APP__.nezam.site> | The released version your real users see. Updates only when you say "release". |

## How you build this app: describe, review, release

You work with an AI coding assistant (Claude Code or similar). Open this
repository in it and describe what you want, in plain English:

> "Add a page that shows a list of tasks, with a button to add a new one."

The AI reads this repo's house rules (`AGENTS.md` — what it may change, what
it must not break, how deploys work) and does the rest:

1. **It proposes the change as a Pull Request.** Nothing is live yet. You
   don't have to read code — ask it to explain the change in plain English,
   then accept (merge) it.
2. **Staging updates automatically.** A few minutes after the merge, the
   change is live on staging. The AI verifies the deploy actually landed and
   tells you when it's ready to try.
3. **You decide when to release.** When staging looks good, say "release
   it" — or use the **Release to Production** button (in the platform
   portal, or GitHub → Actions → release → Run workflow). Production
   updates a few minutes later.

Nothing reaches your users without your go-ahead.

## Where to look things up

- **`docs/`** — plain-language pages about your app (also rendered on the
  portal's *Docs* tab): what it is, how it works, how to develop with AI.
- **`docs/ai-tasks/`** — the AI's task board for this app: what's planned
  (`tasks/todo/`), what's being built (`tasks/in-progress/`), what's done
  (`tasks/done/`). Browse it any time to see where work stands — each task
  has a short summary written for you.
- **`AGENTS.md`** — the house rules the AI follows. You rarely need to read
  it, but everything the AI is and isn't allowed to do is written there.

## Your database, backups, and limits — handled

The platform provides a Postgres database per environment (staging and
production are fully separate), injects the credentials automatically, and
applies schema changes on deploy. Your app has a resource budget suited to
small production apps; the AI knows the numbers and can raise them within
your quota if a feature needs more muscle.

## For developers

The short version (the full contract is in `AGENTS.md`):

- **Stack:** React (Vite) frontend + FastAPI backend + Postgres, shipped as
  one Docker image; FastAPI serves `/api/*` and the built SPA.
- **Tests:** `./scripts/dev.sh` runs the backend suite against a real
  Postgres in docker; `--all` adds Vitest + the production build. CI runs
  the same suite and gates every image build on it.
- **Local dev:** `cd backend && uvicorn app.main:app --port 8080` and
  `cd frontend && npm run dev` (the dev server proxies `/api`).
- **Deploys:** merge to `main` → CI builds + writes the image tag back →
  Flux deploys staging; semver tag (via the release workflow) → production.
  Every deploy is a git commit — the history of `deploy/` is your deploy
  log.
- **Previews:** label a PR `preview` for an ephemeral environment at
  `https://__APP__-pr-<n>.nezam.site` (careful: previews share the staging
  database — see `AGENTS.md`).

## First-time setup (manual copies only)

Created through the platform portal? **Skip this — it's already done.**
Copied the template by hand:

```sh
./scripts/init.sh <your-github-user> <app-name>   # lowercase alnum/dash
git push
```

Then: ask the platform to register the app (namespaces, database, Flux —
platform runbook *"Register a tenant app"*), and after CI's first push make
the `ghcr.io/<user>/<app>` package **public** (GitHub → your profile →
Packages → package settings → Change visibility).
