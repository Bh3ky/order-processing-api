# Known Issues

A working list of problems found while auditing the codebase against [ROADMAP.md](ROADMAP.md). New issues get appended as they are found.

_Last updated: 2026-11-05 (branch `feat/inventory-row-locking`)._

**Severity:** High = wrong behaviour or false confidence; Medium = should fix soon; Low = polish.
**Status:** Open · In progress · Fixed.

| ID | Title | Severity | Phase | Status |
| --- | --- | --- | --- | --- |
| [ISS-001](#iss-001) | Overselling race condition in order creation | High | 5 | In progress |
| [ISS-002](#iss-002) | Lock test passes without testing anything | High | 5 | Fixed |
| [ISS-003](#iss-003) | Inventory-row lock test is empty | High | 5 | Open |
| [ISS-004](#iss-004) | Ruff checks fail on the working tree | Medium | 5 | Open |
| [ISS-005](#iss-005) | Test fixtures cannot exercise concurrency | Medium | 5 | Open |
| [ISS-006](#iss-006) | Rollback tests don't exercise a rollback | Medium | 4 / 12 | Open |
| [ISS-007](#iss-007) | `pytest` listed as a runtime dependency | Low | 1 | Open |
| [ISS-008](#iss-008) | `OrderResponse` schema is not used | Medium | 3 | Open |
| [ISS-009](#iss-009) | `updated_at` columns never update | Medium | 2 | Open |
| [ISS-010](#iss-010) | `Order.status` is unconstrained free text | Low | 2 / 9 | Open |
| [ISS-011](#iss-011) | Foreign keys on `order_items` are not indexed | Low | 2 | Open |
| [ISS-012](#iss-012) | Products router exists but is not registered | Low | 3 | Open |
| [ISS-013](#iss-013) | Order creation logic lives entirely in the endpoint | Low | 11 / 12 | Open |
| [ISS-014](#iss-014) | Dockerfile is development-only | Low | 13 | Open |
| [ISS-015](#iss-015) | Stale TODO comment on `Product.inventory` | Low | 2 | Open |
| [ISS-016](#iss-016) | Test suite not verified during the last audit | Medium | 5 | Fixed |
| [ISS-017](#iss-017) | CI does not cover the test-database setup locally | Low | 13 | Open |

---

## ISS-001: Overselling race condition in order creation

**Severity:** High · **Phase:** 5 · **Status:** In progress (branch `feat/inventory-row-locking`)

**What:** [orders.py](../app/api/v1/endpoints/orders.py) selects inventory rows with a plain `SELECT`, checks `quantity_available` in Python, subtracts, and lets the ORM write back the computed number.

**Why it matters:** two concurrent requests for the last unit can both read `1`, both pass validation, and both write `0`. The `quantity_available >= 0` CHECK constraint does not catch it because neither write is negative. Two orders are created for one unit.

**Fix direction:** `select(Inventory)...with_for_update()` so the second transaction waits for the first to commit, then re-reads the updated quantity. Lock rows in a consistent order (for example `ORDER BY product_id`) to avoid deadlocks when orders contain several products. Keep the 409 behaviour. Roadmap items 5.2 and 5.3.

**Done when:** a test with two real, independent, committing sessions ordering the last unit produces exactly one order and one 409.

## ISS-002: Lock test passes without testing anything

**Severity:** High · **Phase:** 5 · **Status:** Fixed

**What:** in `test_second_transaction_waits_for_row_lock` ([test_order_concurrency.py](../tests/test_order_concurrency.py)), `second_transaction` and the task-creation and assertion block are indented inside `first_transaction`. The test function only defines a coroutine and returns, so no assertion runs.

**Why it matters:** a green test that cannot fail gives false confidence. It also uses an advisory lock, not a row lock, so it does not demonstrate `FOR UPDATE`.

**Fix direction:** dedent the second function and the orchestration block into the test body. Then prove the test can fail (for example, make the second transaction not wait and confirm it goes red). Consider renaming it to say it is an advisory-lock warm-up.

**Result (2026-11-05):** dedented; added a `second_is_asking` event and a 0.5s `pytest.raises(TimeoutError)` window so the check cannot run before B has tried; renamed to `test_second_transaction_waits_for_advisory_lock`. Verified by mutation: removing A's `release_first.wait()` and removing B's lock query both turn the test red (`DID NOT RAISE`). Lesson: a negative assertion ("X did not happen") needs a time window, and a test is only trusted once it has been seen to fail.

## ISS-003: Inventory-row lock test is empty

**Severity:** High · **Phase:** 5 · **Status:** Open

**What:** `test_second_transaction_waits_for_inventory_row_lock` contains only a docstring describing the steps, so it passes trivially.

**Fix direction:** implement the documented steps: commit a product with stock 5; transaction A locks the row with `FOR UPDATE`; transaction B attempts the same lock and must block; A updates and commits; B proceeds and sees the new value. Clean up the committed rows afterwards. Roadmap item 5.1 "isolated database test".

## ISS-004: Ruff checks fail on the working tree

**Severity:** Medium · **Phase:** 5 · **Status:** Open

**What:**
- [test_orders.py](../tests/test_orders.py) line 1 has a stray `from unittest import result` (an accidental IDE auto-import). It shadows the local `result` variables and causes 1 import-order error, 1 unused-import error, and 9 redefinition errors.
- `product= Product(` in `test_create_order_rejects_duplicate_items_exceeding_stock` fails `ruff format`.
- `test_order_concurrency.py` failed `ruff format` (now fixed).

**Why it matters:** CI runs `ruff check` and `ruff format --check`, so a PR would fail. `HEAD` itself was clean; these come from uncommitted changes.

**Fix direction:** delete the stray import, then `uv run ruff format .` and `uv run ruff check .`. Learn how to turn off or review IDE auto-imports.

## ISS-005: Test fixtures cannot exercise concurrency

**Severity:** Medium · **Phase:** 5 / 12 · **Status:** Open

**What:** the `db_session` and `client` fixtures in [conftest.py](../tests/conftest.py) wrap each test in one outer transaction on one connection and hand the same session to the app. That isolates tests well but makes real concurrency impossible: there is one connection, and nothing is ever committed.

**Fix direction:** concurrency tests need their own sessions from `TestSessionFactory`, real commits, and explicit cleanup of the rows they create (or a dedicated schema/database). Decide whether the `client` fixture also needs a "real sessions" variant that overrides `get_db_session` with a fresh session per request.

## ISS-006: Rollback tests don't exercise a rollback

**Severity:** Medium · **Phase:** 4 / 12 · **Status:** Open

**What:** tests such as "does not deduct any inventory when one item is insufficient" pass because validation fails before anything is written. They prove validation order, not rollback.

**Fix direction:** add a test that forces a failure after the deduction but before commit (for example, patch something to raise) and asserts that inventory and orders are unchanged.

## ISS-007: `pytest` listed as a runtime dependency

**Severity:** Low · **Phase:** 1 · **Status:** Open

**What:** `pytest>=9.1.1` was added to `[project].dependencies` in `pyproject.toml` (uncommitted). It is already in the `dev` dependency group.

**Fix direction:** remove it from runtime dependencies and run `uv lock` so the production image does not ship the test runner.

## ISS-008: `OrderResponse` schema is not used

**Severity:** Medium · **Phase:** 3 · **Status:** Open

**What:** [schemas/order.py](../app/schemas/order.py) defines `OrderResponse`, but `create_order` has no `response_model` and returns the ORM object directly. It also omits order items.

**Why it matters:** the API contract is implicit, ORM internals may leak, and the schema/endpoint have drifted apart.

**Fix direction:** set `response_model` on the endpoint and decide the response shape (should it include items?). Read the FastAPI "Response Model" docs first.

## ISS-009: `updated_at` columns never update

**Severity:** Medium · **Phase:** 2 · **Status:** Open

**What:** `Inventory.updated_at` and `Order.updated_at` have `server_default=func.now()` only. After a stock deduction, `inventory.updated_at` still shows the creation time.

**Fix direction:** add `onupdate=func.now()` to the columns (ORM-level, so no migration is needed), or use a database trigger (needs a migration). Understand the difference between ORM-level and DB-level defaults before choosing.

## ISS-010: `Order.status` is unconstrained free text

**Severity:** Low · **Phase:** 2 / 9 · **Status:** Open

**What:** `status` is `String(20)` with no CHECK constraint, and the endpoint writes the literal `"pending"` rather than `OrderStatus.PENDING`.

**Fix direction:** use the enum in code now; add a CHECK constraint or native enum and define valid transitions in Phase 9.

## ISS-011: Foreign keys on `order_items` are not indexed

**Severity:** Low · **Phase:** 2 · **Status:** Open

**What:** PostgreSQL does not index foreign key columns automatically. `order_items.order_id` and `product_id` have no index, so fetching an order's items will scan the table as it grows.

**Fix direction:** add indexes via a migration, and learn to read `EXPLAIN` output to confirm the difference.

## ISS-012: Products router exists but is not registered

**Severity:** Low · **Phase:** 3 · **Status:** Open

**What:** [products.py](../app/api/v1/endpoints/products.py) is empty apart from an unused router, and [router.py](../app/api/v1/router.py) does not include it. There is no way to list products, though "retrieve available products" is a target requirement.

**Fix direction:** decide scope, then add `GET /products` (with inventory level, price, SKU) and register the router.

## ISS-013: Order creation logic lives entirely in the endpoint

**Severity:** Low · **Phase:** 11 / 12 · **Status:** Open

**What:** `create_order` handles validation, locking, stock deduction, totals, and persistence in one function. Acceptable while learning, but it makes testing and reuse harder and conflicts with the "clean architecture / separation of concerns" goal.

**Fix direction:** after Phase 5, discuss extracting a service layer. Do not refactor before the concurrency work is verified.

## ISS-014: Dockerfile is development-only

**Severity:** Low · **Phase:** 13 · **Status:** Open

**What:** the image runs `uvicorn --reload`, installs dev-oriented dependencies, and Compose bind-mounts the source tree.

**Fix direction:** in Phase 13, build a separate production image (no `--reload`, no dev dependencies, non-root user, smaller layers).

## ISS-015: Stale TODO comment on `Product.inventory`

**Severity:** Low · **Phase:** 2 · **Status:** Open

**What:** [product.py](../app/models/product.py) still says "TODO: add relationship between product and inventory" above the relationship that already exists.

**Fix direction:** delete the TODO; consider `uselist=False` explicitly to make the one-to-one intent clear.

## ISS-016: Test suite not verified during the last audit

**Severity:** Medium · **Phase:** 5 · **Status:** Fixed

**What:** the audit on 2026-11-05 could not run the suite against PostgreSQL because Docker was not running. Only static review and Ruff were done. The "Run the test suite" tick in Phase 4 therefore has not been re-confirmed since the uncommitted changes.

**Fix direction:** `docker compose up -d`, ensure the test database exists and is migrated (see README), then `uv run pytest`. Record the result here.

**Result (2026-11-05):** test DB confirmed reachable and migrated; full suite ran with 22 tests passing. Note that two of the three concurrency tests pass vacuously (ISS-002, ISS-003), so green does not yet mean the locking behaviour is verified.

## ISS-017: Local test-database setup is undocumented in code

**Severity:** Low · **Phase:** 13 · **Status:** Open

**What:** CI creates and migrates `order_processing_test` automatically; locally, Compose only creates `order_processing`, so the test database must be created and migrated by hand. This was previously undocumented (now described in the README).

**Fix direction:** consider an init script or a Compose service/Makefile target that creates and migrates the test database, so the setup is reproducible.
