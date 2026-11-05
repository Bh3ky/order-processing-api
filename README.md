# Order Processing API

A production-inspired REST API for placing and tracking customer orders, built with FastAPI, SQLAlchemy 2.x (async), and PostgreSQL.

## Problem statement

Order processing systems directly affect customers and revenue. Typical failures include:

- A customer submits an order, loses connectivity, and retries, creating a **duplicate order**.
- Two customers buy the **last unit** of a product at the same moment, causing **overselling**.
- Payment processing takes seconds and should **not block** the API.
- During an incident, engineers need to **trace one customer's request** across services.

Solving these takes more than inserting rows: it needs transactional guarantees, idempotent request handling, asynchronous workflows, structured logging, and robust error handling.

## Status

| Area | State |
| --- | --- |
| Project foundation (uv, async SQLAlchemy, Alembic, pytest, Ruff, Docker Compose, CI) | Done |
| Data model: products, inventory, orders, order items | Done |
| `POST /api/v1/orders` with server-side totals and price snapshots | Done |
| Inventory validation and atomic deduction (HTTP 409 on conflict) | Done |
| Concurrency control (PostgreSQL row-level locking) | **In progress** |
| Idempotency keys | Planned |
| Redis caching and rate limiting | Planned |
| RabbitMQ background jobs and transactional outbox | Planned |
| Simulated payments and order lifecycle | Planned |
| Authentication and security | Planned |
| Structured logging, correlation IDs, observability | Planned |
| Production deployment | Planned |

Redis and RabbitMQ are part of the target architecture but are **not yet used** by the code. See the [roadmap](docs/ROADMAP.md) for the full plan.

### Implemented endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Checks the API and the database connection |
| `POST` | `/api/v1/orders` | Creates an order, validates stock, deducts inventory |

`POST /api/v1/orders` request body:

```json
{
  "items": [
    { "product_id": "3f2b8c1e-0000-0000-0000-000000000000", "quantity": 2 }
  ]
}
```

Responses: `201` created, `404` a product does not exist, `409` insufficient inventory, `422` invalid request body.

Interactive OpenAPI docs are served at `/docs` when the API is running.

## Target requirements

These are the capabilities the finished system should have. Items that are not built yet are marked in the [roadmap](docs/ROADMAP.md).

### Functional

- Retrieve available products with SKU, price, and inventory level.
- Place orders with one or more items; receive an order identifier.
- Validate all incoming requests.
- Verify and reserve inventory atomically; never allow negative stock; roll back on failure.
- Require an `Idempotency-Key` on `POST /orders`: detect duplicates, return the original response, reject conflicting payloads that reuse a key.
- Publish background tasks on order creation (payment, confirmation email, analytics event, audit log) without making the client wait.
- Retrieve order details, items, status, and creation timestamp.

### Non-functional

- *Reliability:* ACID transactions, no duplicate orders, inventory consistency, safe retries.
- *Performance:* fast responses, expensive work offloaded, frequently requested data cached.
- *Scalability:* multiple API and worker instances.
- *Maintainability:* separation of concerns, dependency injection, migrations, automated tests.
- *Observability:* a correlation ID and request ID on every request, structured JSON logs, error tracing.

## Tech stack

| Layer | Technology | Purpose | Status |
| --- | --- | --- | --- |
| Language | Python 3.13 | Backend development | In use |
| Framework | FastAPI | REST API | In use |
| Validation | Pydantic v2 | Request validation and settings | In use |
| ORM | SQLAlchemy 2.0 (async, psycopg 3) | Database access | In use |
| Migrations | Alembic | Schema migrations | In use |
| Database | PostgreSQL 17 | Persistent storage | In use |
| Testing | pytest, pytest-asyncio, HTTPX | Automated tests | In use |
| Tooling | uv, Ruff | Dependencies, lint, format | In use |
| Containers | Docker, Docker Compose | Local development | In use |
| CI | GitHub Actions | Lint, migrate, test | In use |
| Cache | Redis | Caching, rate limiting | Planned |
| Queue | RabbitMQ | Background jobs | Planned |
| Logging | structlog / standard logging | Structured logs | Planned |

## Project structure

```text
app/
  main.py                 FastAPI application
  api/v1/                 Routers and endpoints (health, orders)
  core/config.py          Settings loaded from environment
  database/               Engine, session factory, session dependency
  models/                 SQLAlchemy models (Product, Inventory, Order, OrderItem)
  schemas/                Pydantic request/response schemas
alembic/                  Migration environment and versions
tests/                    pytest suite
docs/                     Roadmap, issues, database design
```

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose

### 1. Configure the environment

Create `.env.local` in the project root (it is git-ignored; see `.env.example` for the variable names):

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/order_processing
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/order_processing_test
```

`DATABASE_URL` uses the host `db` because the API runs inside the Compose network. `TEST_DATABASE_URL` uses `localhost:5433` because tests run on your machine and PostgreSQL is published on port 5433.

### 2. Start the services

```bash
docker compose up -d
```

### 3. Apply migrations

```bash
docker compose exec api uv run alembic upgrade head
```

The API is then available at <http://localhost:8000> (docs at <http://localhost:8000/docs>).

### 4. Prepare the test database (one time)

Tests run against a separate database, which must exist and be migrated:

```bash
docker compose exec db psql -U postgres -c "CREATE DATABASE order_processing_test;"
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/order_processing_test uv run alembic upgrade head
```

### 5. Run the checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

More commands (logs, rebuilds, Alembic) are in [COMMANDS.md](COMMANDS.md).

## Design notes

- **Prices are snapshotted.** Each order item stores the unit price at purchase time, so later price changes never alter historical orders.
- **The server is authoritative for totals.** Clients never send prices or totals.
- **Money uses `NUMERIC(12,2)`**, never floating point.
- **Invariants live in the database too.** CHECK constraints stop negative stock, non-positive quantities, and negative prices even if application code has a bug.
- **Stock changes and order creation share one transaction**, so a failure cannot leave half an order.
- **Duplicate product lines are aggregated** before stock validation, so splitting a purchase across lines cannot bypass the stock check.

More detail: [docs/database-design.md](docs/database-design.md).

## Known limitations

Under concurrent requests the current stock check can still oversell, because rows are not yet locked. Row-level locking is the work in progress. The full list of known problems is in [docs/ISSUES.md](docs/ISSUES.md).

## Documentation

- [docs/ROADMAP.md](docs/ROADMAP.md): phased learning roadmap and status
- [docs/ISSUES.md](docs/ISSUES.md): known issues and follow-ups
- [docs/database-design.md](docs/database-design.md): schema design decisions
- [COMMANDS.md](COMMANDS.md): command cheat sheet

## License

See [LICENSE](LICENSE).
