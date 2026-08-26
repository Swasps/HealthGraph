# HealthGraph

A healthcare data aggregation backend that exposes a unified GraphQL API over
patient records collected from disparate clinical services (encounters,
diagnoses, medications, allergies, lab results, vital signs). Built to
exercise the parts of backend engineering that a plain CRUD API glosses
over: query batching, cache invalidation, role- and field-level
authorization, and query-cost control on a public-ish GraphQL surface.

## Status

Under active development. See commit history for progress; each commit is a
self-contained slice of the system (models, then repositories, then auth,
then the GraphQL layer, then performance work, then tests).

## Stack

- **API**: FastAPI + Strawberry GraphQL, REST for admin/system endpoints
- **Data**: PostgreSQL via SQLAlchemy 2.0 (async) + Alembic migrations
- **Cache**: Redis (read-through caching, rate limiting)
- **Auth**: JWT access/refresh tokens, RBAC + patient-scoped authorization
- **Testing**: Pytest (unit, integration, e2e)
- **Infra**: Docker Compose, GitHub Actions CI

## Why this exists

Most "healthcare API" side projects stop at exposing tables over GraphQL.
This one treats the interesting problems as the point:

- a doctor querying `patient(id)` should not see patients they have no
  clinical relationship with — authorization is enforced per-object, not
  just per-endpoint
- `patientTimeline` merges six different record types into one chronological
  feed without N+1 fan-out, using per-request DataLoaders
- GraphQL queries are cost-limited (depth + complexity) before they ever
  reach the database
- every access to patient data is audited

Further documentation (architecture, ERD, API reference, security model,
performance benchmarks) lands in later commits as those pieces are built.

## Local development

Full setup instructions will be added once the Docker Compose stack and
Alembic migrations are in place (see `ARCHITECTURE.md` once published).

## License

MIT — see [LICENSE](LICENSE).
