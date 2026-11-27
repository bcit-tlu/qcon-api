# AGENTS.md

Tooling: every CLI this repo needs comes from `shell.nix`; run commands via `nix-shell --run` (or `direnv allow`) before concluding a tool is missing.

## Setup Commands

- Local development: `docker compose up --build` (starts Django + PostgreSQL)
- Run Django dev server (inside container): `python manage.py runserver 0.0.0.0:8000`
- Run migrations: `python manage.py migrate`
- Create superuser: `python manage.py createsuperuser`
- Helm lint: `helm lint charts/`
- Helm validate: `helm template test charts/ | kubeconform -strict -summary -schema-location default -ignore-missing-schemas`

## Code Style

- Follow PEP 8 and existing code conventions
- Use type annotations where practical
- Follow conventional commit format for PR titles
- License: MPL-2.0

## Project Structure

- `/qcon` — Django project settings, ASGI/WSGI config, URL routing
- `/api` — Main API app (models, views, serializers, WebSocket consumers, Celery tasks)
- `/restapi` — REST API app (RootPath view serves as health check at `/`)
- `/antlr` — ANTLR grammar files and Java parsers (formatter, sectioner, splitter, questionparser, endanswers)
- `/pandoc` — Pandoc conversion scripts and filters
- `/charts` — Helm chart for Kubernetes deployment (flat layout)
- `/.github/workflows/` — CI/CD pipelines
- `/docker-entrypoint.sh` — Container bootstrap: migrations, Redis, Celery workers, then exec

## Architecture

- **Runtime**: Django ASGI via Daphne on port 8000 (not nginx — this is a Python API, not a static site)
- **Background workers**: Celery with 4 workers, backed by Redis (started in-container by entrypoint)
- **Database**: PostgreSQL with dynamic credential rotation via Vault (`postgresql_dynamic` backend)
- **WebSockets**: Django Channels via `TextConsumer` for real-time conversion feedback
- **Document processing**: ANTLR Java parsers + Pandoc pipeline (Word → structured HTML/JSON → SCORM ZIP)
- **Health endpoint**: `GET /` returns 200 with app version (via `restapi.views.RootPath`)

## Development Workflow

- Default PR loop (no need to be asked): after every push, wait until all checks — including Devin Review and github-code-quality — have finished, fix and resolve every thread (≤3 rounds), and only then report or admin-merge. An instruction to "admin-merge" never skips this wait.
- Create feature branches from `main`
- Use pull requests for code review
- PR titles must follow conventional commit format (enforced by `pr-title-lint.yaml`)
- Squash commits before merging

## CI/CD

- CI uses shared `bcit-tlu/.github` OCI build reusable workflow
- `helm-lint` validates Helm charts on every push and PR
- `release-please` manages versioning via conventional commits (`release-type: "simple"`)
- Version is tracked in `.release-please-manifest.json` and `Chart.yaml` (`# x-release-please-version` annotations)
- Images are published to `ghcr.io/bcit-tlu/qcon-api/qcon-api`
- Charts are published to `oci://ghcr.io/bcit-tlu/qcon-api/charts`
- `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` is set in all workflows

## Deployment

- Deployed to Kubernetes via Flux CD (see `bcit-tlu/flux-fleet`)
- Ingress: `qcon-api.<CLUSTER_ENV>.ltc.bcit.ca`
- Vault provides dynamic PostgreSQL credentials and Kubernetes auth
- Both `latest` (cluster03) and `stable` (cluster04) overlays exist
