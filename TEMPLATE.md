# template-fastapi-react — maintainer notes

> **This file never ships to apps** — `scripts/init.sh` and the portal
> scaffolder delete it (like `VERSION`). Everything here is for people
> maintaining the template itself. The scaffolded-app-facing README is
> `README.md` (written for app owners, placeholders filled at scaffold
> time).

## What this template is

Batteries-included app template for the nezam platform: React (Vite)
frontend + FastAPI backend + Postgres, shipped as **one image**, deployed by
Flux to `https://<app>-staging.nezam.site` and `https://<app>.nezam.site`.
Ships with: tests + a CI test gate, migrations-on-start, a staging writeback
pipeline (ADR-028), a Release-to-Production workflow, preview environments,
TechDocs, a Backstage catalog entry, and an `AGENTS.md` that doubles as the
AI agent's operating manual (task board in `docs/ai-tasks/`, deploy
verification, runtime budget, security checklist, template upgrade skill).

## How apps are created from it

- **Portal (normal path):** the Backstage scaffolder copies the repo,
  substitutes the double-underscore placeholders everywhere, stamps
  `nezam.space/template-version` from `VERSION`, then deletes `VERSION` and
  `TEMPLATE.md`.
- **Manual:** GitHub "Use this template" (or plain copy), then
  `./scripts/init.sh <user> <app>` — does the same substitution + cleanup.
  Registration on the platform is the runbook's "Register a tenant app".

## Release discipline (versioning)

Scaffolded apps record their origin in `catalog-info.yaml`
(`nezam.space/template-version`), and the AI upgrade skill in the scaffold's
`AGENTS.md` walks diverged apps up the version ladder. That only works with
release discipline:

- `VERSION` at the repo root holds the current release tag (e.g. `v1.2.0`)
  and MUST equal the latest `vX.Y.Z` git tag on `main`.
- Every content change ships as a PR that ALSO bumps `VERSION`; tag the
  squash-merge commit with that exact version IMMEDIATELY after merging.
- Semver intent: patch = fixes, minor = additive, major = breaks the platform
  contract / needs app-side rework.
- Tags are additive and PERMANENT (apps stamp them; the upgrade skill
  compares tag..tag) — never delete or move one; fix forward.
- CI's own `deploy: staging → …` writeback commits never bump `VERSION`; the
  upgrade skill ignores that churn.
- Full maintainer procedure (branch, edit, merge, tag): platform repo
  runbook, "Evolve the app template".

Apps stay fully self-contained (no shared workflows / remote bases) on
purpose — platform ADR-026: the repo must run standalone anywhere.

## Placeholder rules

- Tokens: `__USER__`, `__APP__`, `__TEMPLATE_VERSION__` — substituted across
  the whole tree by the portal, and by `init.sh` across `deploy/`,
  `catalog-info.yaml`, `AGENTS.md`, `README.md`, `mkdocs.yml`, `docs/*.md`.
- Never write a literal token in prose that merely TALKS ABOUT tokens
  (see the upgrade-skill section in `AGENTS.md` for the workaround wording),
  or scaffolding will substitute it.
- New files with no placeholders (tests, `scripts/dev.sh`, `docs/ai-tasks/`)
  need no init.sh changes; files with placeholders must be covered by the
  init.sh substitution list.
