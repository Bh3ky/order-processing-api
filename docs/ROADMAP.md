# Order Processing API — Learning Roadmap

**Project:** `order-processing-api`
**Primary objective:** Build a production-minded order processing backend while developing a proper understanding of FastAPI, SQLAlchemy, PostgreSQL, transactions, concurrency, testing, and backend system design.

**Current position:** Core order creation and inventory deduction are complete. We are working on database concurrency control, specifically PostgreSQL row-level locking (Phase 5).

_Last audited against the codebase: 2026-11-05 (branch `feat/inventory-row-locking`)._

## Status legend

- **Completed** — implemented and verified.
- **In progress** — current work.
- **Planned** — not yet started.
- **Verify** — progress needs confirmation.

## Overall tracker

| Phase | Focus                                       | Status   |
| ----- | ------------------------------------------- | -------- |
| 1     | Project foundation                          | Done (README outstanding) |
| 2     | Database modelling and persistence          | Done (minor follow-ups)   |
| 3     | Core Order API                              | Done (minor follow-ups)   |
| 4     | Inventory management                        | Done (minor follow-ups)   |
| 5     | Concurrency control                         | Current  |
| 6     | Idempotency                                 | Next     |
| 7     | Caching and rate limiting                   | Planned  |
| 8     | Background jobs and event-driven processing | Planned  |
| 9     | Payment simulation and order lifecycle      | Planned  |
| 10    | Authentication and security                 | Planned  |
| 11    | Error handling and observability            | Planned  |
| 12    | Testing strategy                            | Planned  |
| 13    | CI/CD and deployment                        | Planned  |
| 14    | Documentation and portfolio                 | Planned  |

## The engineering cycle (applies to every phase)

1. **Understand:** explain the underlying problem and relevant concepts.
2. **Design:** decide where the responsibility belongs and why.
3. **Implement:** break the feature into small tasks.
4. **Test:** verify normal behaviour, edge cases, and failure scenarios.
5. **Review:** inspect the code, design trade-offs, and potential weaknesses.
6. **Document:** record what we learned in the Notion engineering notes.
7. **Commit:** small, meaningful Git commits on feature branches.

At the end of each phase, reflect on: what we built, what we learned, what could break at scale, and what we would improve.

**Out of scope for now:** a full user-account platform unless it becomes necessary; real card processing and PCI compliance; Redis-based inventory locking before we have evaluated whether it is needed.

---

## Phase 1 — Project foundation

**Status: Completed** (one item outstanding)

Establish a maintainable development environment and project structure.

- [x] Create the FastAPI project.
- [x] Configure Python and dependency management with uv.
- [x] Establish application structure and separation of concerns.
- [x] Configure environment variables and application settings.
- [x] Configure PostgreSQL.
- [x] Set up SQLAlchemy 2.x asynchronous database access.
- [x] Configure database session dependencies.
- [x] Set up Alembic migrations.
- [x] Configure pytest and pytest-asyncio.
- [x] Configure Ruff for linting and formatting.
- [ ] Review the README and ensure setup instructions accurately reflect the current project.

**What this teaches:** Python project organisation, environment configuration, dependency management, database connectivity, and application structure.

**Audit notes**
- README is still a stub: it lists Redis and RabbitMQ as part of the stack, but neither exists yet, and it has no setup instructions. `COMMANDS.md` holds the real commands. This unchecked item is correctly unchecked.
- `pytest` was added to runtime `dependencies` in `pyproject.toml` (uncommitted). It is already in the `dev` group; it probably should not be a runtime dependency.
- `.env.local` uses host `db` for `DATABASE_URL` (Docker network) but `localhost:5433` for `TEST_DATABASE_URL` (host machine). That works, but it is the kind of thing the README must explain.

## Phase 2 — Database modelling and persistence

**Status: Completed**

Build the underlying data model before implementing business workflows.

- [x] Create the Product model.
- [x] Create the Order model.
- [x] Create the OrderItem model.
- [x] Define relationships and foreign keys.
- [x] Configure constraints and appropriate data types.
- [x] Generate and apply database migrations.
- [x] Understand SQLAlchemy models versus database tables.
- [x] Persist order items as relational records.
- [x] Store product price snapshots on order items.
- [x] Calculate line totals.
- [x] Calculate order totals on the server rather than trusting client input.

**Important design decision:** the order item stores the price at the time of purchase, so later product price changes do not alter historical orders.

**What this teaches:** relational database design, ORM relationships, constraints, migrations, and data integrity.

**Audit notes (verified in code; all ticks hold)**
- `NUMERIC(12,2)` for money, CHECK constraints on prices, quantities, totals, and inventory; `unique` on `sku` and `inventory.product_id`. The migration matches the models.
- Follow-ups (not blockers):
  - [ ] `Inventory.updated_at` and `Order.updated_at` only have a `server_default`; nothing updates them on change, so `inventory.updated_at` is stale after every deduction. Learn `onupdate=func.now()` and its trade-offs.
  - [ ] `Order.status` is a plain `String(20)` with no CHECK constraint, and the endpoint writes the literal `"pending"` instead of `OrderStatus.PENDING`. Revisit in Phase 9.
  - [ ] `order_items.order_id` / `product_id` have no indexes (PostgreSQL does not auto-index foreign keys).
  - [ ] Remove the stale `TODO` comment above `Product.inventory` (the relationship exists).

## Phase 3 — Core Order API

**Status: Completed** (one gap)

Build the basic order creation workflow.

- [x] Implement order creation.
- [x] Define request and response schemas.
- [x] Validate requested products.
- [x] Reject requests containing nonexistent products.
- [x] Persist orders.
- [x] Persist individual order items.
- [x] Calculate authoritative order totals.
- [x] Return appropriate HTTP responses.
- [x] Test successful order creation.
- [x] Test invalid product scenarios.

**What this teaches:** HTTP request handling, Pydantic validation, API design, database persistence, and business logic.

**Audit notes**
- `OrderResponse` is defined in `app/schemas/order.py` but is **not used**: `create_order` has no `response_model` and returns the ORM object directly. "Define response schemas" is only half done.
  - [ ] Wire `OrderResponse` (or an items-inclusive variant) in as `response_model` so the API contract is explicit and does not leak ORM internals.
- `app/api/v1/endpoints/products.py` exists but is not registered in the router, and no product endpoints exist. Tests create products directly via the session. Decide whether product endpoints are in scope.
- The create-order endpoint contains all business logic. Acceptable for now; extracting a service layer is a good Phase 11/12 refactor discussion.

## Phase 4 — Inventory management

**Status: Completed** — correct under sequential requests only; see Phase 5.

Introduce stock management into the order creation workflow.

- [x] Create the Inventory model.
- [x] Establish the relationship between products and inventory.
- [x] Enforce non-negative inventory quantities.
- [x] Validate available stock before creating an order.
- [x] Deduct inventory when an order is created.
- [x] Reject orders when stock is insufficient.
- [x] Return HTTP 409 Conflict for inventory conflicts.
- [x] Ensure inventory deduction and order creation happen within the same database transaction.
- [x] Test insufficient inventory.
- [x] Test multiple products in one order.
- [x] Test that failed validation does not leave partial orders or inventory deductions.
- [x] Identify and fix duplicate-product lines bypassing stock validation.
- [x] Test aggregated quantities for duplicate product lines.
- [x] Run the test suite.
- [x] Run Ruff linting and formatting checks.

**Important lesson:** business logic must account for the shape of real-world requests, not just the happy path. Duplicate product lines exposed a genuine inventory validation bug.

**Audit notes**
- Logic verified by reading the code: quantities are aggregated per product before validation; all validation happens before any deduction; one `commit()` covers the order, items, and stock changes; 409 for missing inventory row or insufficient stock.
- The duplicate-line fix and its two tests (`test_create_order_rejects_duplicate_items_exceeding_stock`, `test_create_order_deducts_aggregated_duplicate_items`) are **uncommitted** on the current branch.
- Why this is not yet safe under concurrency: the endpoint reads `quantity_available` into Python, subtracts, and lets the ORM write back the computed value. Two requests can read the same value and both write the same result (a lost update). The CHECK constraint cannot catch this because neither write is negative. This is the Phase 5 problem.
- The "failed validation leaves no partial state" tests are weaker than they look: validation fails before anything is written, so they do not exercise a real rollback. A genuine rollback test needs a failure _after_ the deduction (e.g. a forced error before commit).
- **Ruff status: currently failing** on the working tree (see Phase 5 audit). HEAD was clean; the failures come from uncommitted changes.
- **Test suite status:** could not be run during this audit because PostgreSQL (Docker) was not running. Re-run before ticking anything in Phase 5.

## Phase 5 — Database concurrency control

**Status: In progress**

**Problem:** two customers may attempt to purchase the same inventory simultaneously. Both transactions could read the same available quantity before either deducts stock. The database must coordinate these operations.

### 5.1 Understand transaction locking

- [x] Understand the inventory overselling race condition.
- [x] Understand why ordinary stock validation is insufficient under concurrency.
- [x] Understand database transactions.
- [x] Understand transaction commit and rollback.
- [x] Understand row-level locks.
- [x] Understand why different inventory rows can be locked independently.
- [x] Understand why locks are released when transactions commit or roll back.
- [x] Learn about PostgreSQL `SELECT ... FOR UPDATE`.
- [ ] Complete an isolated database test demonstrating row-level locking.

### 5.2 Implement row-level locking

- [ ] Add `.with_for_update()` to the inventory selection query.
- [ ] Acquire inventory locks before validating stock.
- [ ] Ensure the locks remain held until the order transaction finishes.
- [ ] Consider consistent lock ordering when multiple products are involved (prevents deadlocks, e.g. `ORDER BY product_id`).
- [ ] Preserve existing 409 Conflict behaviour.

### 5.3 Verify concurrency behaviour

- [ ] Test two independent sessions accessing the same inventory row.
- [ ] Test that a second transaction waits for the first.
- [ ] Test that the second transaction sees the updated inventory quantity.
- [ ] Test concurrent order requests for the same product.
- [ ] Verify that overselling cannot occur.
- [ ] Verify that unrelated inventory rows can still be processed independently.
- [ ] Run the full test suite.
- [ ] Run Ruff checks.

**What this teaches:** ACID transactions, isolation, locking, race conditions, concurrent database sessions, and transaction boundaries.

**Audit notes — current state of `tests/test_order_concurrency.py` (untracked)**
- `test_concurrent_sessions_use_distinct_connections`: a sound idea (two sessions, `pg_backend_pid()`, barrier). Fine once the DB is up.
- `test_second_transaction_waits_for_row_lock`: **passes vacuously.** `second_transaction` and the task-creation/assertion block are indented _inside_ `first_transaction`, so the test function only defines a coroutine and returns. No assertion ever runs. It also uses an advisory lock, not a row lock, so it does not demonstrate `FOR UPDATE` anyway (fine as a warm-up, but name it honestly).
- `test_second_transaction_waits_for_inventory_row_lock`: contains only a docstring. It passes trivially.
- A passing test is not evidence. Before ticking 5.1's last item, make each test able to _fail_ (e.g. temporarily remove the lock and confirm the test goes red).
- Design constraint for 5.3: the `db_session` / `client` fixtures wrap everything in one outer transaction on one connection, which cannot demonstrate concurrency. Concurrency tests need independent sessions that really commit, plus explicit cleanup of the rows they create.
- `.with_for_update()` is not yet in `create_order`; the inventory query in [orders.py](../app/api/v1/endpoints/orders.py) is still unlocked.

**Working-tree hygiene before this phase's commits**
- `tests/test_orders.py`: stray `from unittest import result` (an accidental IDE auto-import) shadows the local `result` variables → 1 import-order error + 1 unused-import + 9 redefinition errors from `ruff check`; `product= Product(` fails `ruff format`.
- `tests/test_order_concurrency.py`: fails `ruff format`.
- `pyproject.toml` / `uv.lock`: `pytest` added as a runtime dependency (see Phase 1).
- Suggested commit split: (1) duplicate-line fix + tests, (2) concurrency tests, (3) `with_for_update` change.

This is an important milestone: it moves the application from working under ordinary conditions towards handling concurrent production traffic.

## Phase 6 — Idempotency

**Status: Planned**

**Problem:** clients retry requests because of network failures or timeouts. Without protection, the same order could be created more than once.

- [ ] Understand idempotent versus non-idempotent HTTP operations.
- [ ] Understand idempotency keys.
- [ ] Design an idempotency key persistence strategy.
- [ ] Add an idempotency key to order creation.
- [ ] Enforce uniqueness at the database level.
- [ ] Return the original result when a request is retried.
- [ ] Test duplicate requests.
- [ ] Test concurrent requests using the same idempotency key.
- [ ] Test failure and retry scenarios.

**What this teaches:** distributed systems, retry semantics, uniqueness constraints, and reliable API design.

## Phase 7 — Caching and rate limiting

**Status: Planned**

Introduce Redis as an application infrastructure component.

- [ ] Understand caching and when it is appropriate.
- [ ] Understand cache-aside and expiration strategies.
- [ ] Set up Redis.
- [ ] Implement a small caching use case.
- [ ] Understand rate limiting algorithms.
- [ ] Implement API rate limiting.
- [ ] Handle Redis connection failures.
- [ ] Test rate-limit behaviour.
- [ ] Evaluate cache invalidation and consistency.

**What this teaches:** Redis, caching strategies, request protection, and infrastructure dependencies.

## Phase 8 — Background jobs and event-driven processing

**Status: Planned**

Some operations should not block the HTTP request while they execute.

- [ ] Understand synchronous versus asynchronous work.
- [ ] Understand background job queues.
- [ ] Introduce RabbitMQ.
- [ ] Design a background task workflow.
- [ ] Implement asynchronous order-related processing.
- [ ] Understand message acknowledgements.
- [ ] Understand retries and failed messages.
- [ ] Introduce the transactional outbox pattern.
- [ ] Understand why database commits and message publishing can become inconsistent.
- [ ] Test job processing and failure scenarios.

**What this teaches:** message brokers, distributed processing, eventual consistency, reliability, and asynchronous architectures.

## Phase 9 — Payment simulation and order lifecycle

**Status: Planned**

Introduce a payment workflow without integrating real card processing.

- [ ] Define order lifecycle states.
- [ ] Define valid order state transitions.
- [ ] Understand payment state versus order state.
- [ ] Design a simulated payment service.
- [ ] Implement payment success and failure scenarios.
- [ ] Handle payment-related retries.
- [ ] Ensure duplicate payment events do not create inconsistent state.
- [ ] Test order lifecycle transitions.

**Scope constraint:** this is a simulated payment workflow, not a real payment gateway or PCI-compliant payment system.

**What this teaches:** state machines, business workflows, service boundaries, and payment integration concepts.

## Phase 10 — Authentication and security

**Status: Planned**

Introduce access control and API security.

- [ ] Understand authentication versus authorization.
- [ ] Understand password hashing.
- [ ] Design a minimal authentication approach.
- [ ] Implement token-based authentication.
- [ ] Protect relevant API endpoints.
- [ ] Introduce role-based authorization where appropriate.
- [ ] Validate and sanitize incoming data.
- [ ] Review secrets management.
- [ ] Review database permissions.
- [ ] Review security-related HTTP headers and error responses.
- [ ] Test unauthorized and forbidden requests.

**What this teaches:** identity, access control, credential management, and API security.

## Phase 11 — Error handling and observability

**Status: Planned**

Make the application easier to debug and operate.

- [ ] Introduce centralized exception handling.
- [ ] Standardise API error responses.
- [ ] Distinguish expected business errors from unexpected system errors.
- [ ] Introduce structured logging.
- [ ] Add request correlation IDs.
- [ ] Understand metrics, logs, and traces.
- [ ] Monitor database performance.
- [ ] Monitor background job failures.
- [ ] Add health-check endpoints (a basic `/health` already exists; extend it).
- [ ] Test error handling and observability behaviour.

**What this teaches:** production debugging, monitoring, operational reliability, and incident investigation.

## Phase 12 — Testing strategy

**Status: Planned**

Expand beyond basic endpoint tests.

- [ ] Review unit versus integration versus end-to-end tests.
- [ ] Improve test fixture isolation.
- [ ] Test database transaction behaviour.
- [ ] Test concurrent requests.
- [ ] Test failure and rollback scenarios.
- [ ] Test background workers.
- [ ] Test authentication and authorization.
- [ ] Introduce test factories where useful.
- [ ] Understand test coverage and its limitations.

**What this teaches:** testing strategy, deterministic test design, integration testing, and confidence in system behaviour.

## Phase 13 — CI/CD and deployment

**Status: Planned** (a basic CI workflow already exists)

Prepare the application for deployment.

- [ ] Create a GitHub Actions workflow (exists: Ruff, migrations, pytest against a Postgres service; extend as needed).
- [ ] Run Ruff checks automatically (exists).
- [ ] Run automated tests in CI (exists).
- [ ] Configure test database services for CI (exists).
- [ ] Build a production Docker image (current Dockerfile is development-oriented: `--reload`, bind-mount in compose).
- [ ] Review Dockerfile security and image size.
- [ ] Configure production environment variables.
- [ ] Configure database migrations during deployment.
- [ ] Deploy the API.
- [ ] Verify health checks and application logs.
- [ ] Document deployment and rollback procedures.

**What this teaches:** CI/CD, Docker, deployment, environment management, and release engineering.

## Phase 14 — Documentation and portfolio presentation

**Status: Planned**

Turn the project into a credible portfolio artifact.

- [ ] Write a clear project README.
- [ ] Document the system architecture.
- [ ] Add an architecture diagram.
- [ ] Document database entities and relationships (started: [database-design.md](database-design.md)).
- [ ] Document API endpoints.
- [ ] Publish OpenAPI documentation.
- [ ] Document important design decisions.
- [ ] Document transaction and concurrency handling.
- [ ] Document testing strategy.
- [ ] Document deployment instructions.
- [ ] Include known limitations and future improvements.
- [ ] Review Git commit history for meaningful changes.
- [ ] Prepare a concise project case study for interviews.

**What this teaches:** technical communication, architectural reasoning, documentation, and engineering decision-making.

---

## Are we drifting off track?

No. The progression is intentional:

1. Learn to create and persist orders.
2. Introduce inventory validation and deduction.
3. Discover that ordinary validation does not protect against concurrent requests.
4. Learn how PostgreSQL locking solves that problem.
5. Once concurrency is handled, idempotency addresses duplicate requests and retries.

These are related but distinct engineering problems; do not skip one because another looks similar.

We are not just producing a working API. We are learning why its design works, what can fail, and how to prove correctness through tests.
