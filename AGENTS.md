# AGENTS.md

## Setup Commands

- Local development: `docker compose up --build`
- Run Django dev server (inside container): `python manage.py runserver 0.0.0.0:8000`
- Run migrations: `python manage.py migrate`
- Create superuser: `python manage.py createsuperuser`

## Code Style

- Follow PEP 8 and existing code conventions
- Use type annotations where practical
- Follow conventional commit format for PR titles

## Project Structure

- `/qcon` — Django project settings, ASGI/WSGI config, URL routing
- `/api` — Main API app (models, views, serializers, WebSocket consumers, Celery tasks)
- `/restapi` — REST API app (alternative API interface)
- `/antlr` — ANTLR grammar files and Java parsers (formatter, sectioner, splitter, questionparser, endanswers)
- `/pandoc` — Pandoc conversion scripts and filters
- `/charts` — Helm chart for Kubernetes deployment

## Development Workflow

- Create feature branches from `main`
- Use pull requests for code review
- PR titles must follow conventional commit format (enforced by CI)
- Squash commits before merging
- Update documentation for new features

## CI/CD

- CI uses shared `bcit-tlu/.github` OCI build reusable workflow
- `helm-lint` validates Helm charts on every push and PR
- `release-please` manages versioning via conventional commits
- Images are published to `ghcr.io/bcit-tlu/qcon-api/qcon-api`
- Charts are published to `oci://ghcr.io/bcit-tlu/qcon-api/charts`
