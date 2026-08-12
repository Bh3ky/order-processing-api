# Commands

1. Starting the development environment

```bash
docker compose up -d
```

2. Checking running services

```bash
docker compose ps
```

3. Viewing logs

```bash
docker compose logs -f
```

4. Stopping the development environment

```bash
docker compose down
```

5. Rebuilding the API image

```bash
docker compose build api
```

6. Rebuilding and restarting the environment

```bash
docker compose up -d --build
```

7. Rebuilding and restarting a specific service

```bash
docker compose up -d --build api
```

## FastAPI

1. Running the API locally

```bash
uv run uvicorn app.main:app --reload
```

2. Running the API inside Docker

```bash
docker compose exec api uv run uvicorn app.main:app
```

## Database / Alembic

1. Chcecking current migration

```bash
docker compose exec api uv run alembic current
```

2. Generating a migration

```bash
docker compose exec api uv run alembic revision --autogenerate -m "migration message"
```

3. Applying migrations

```bash
docker compose exec api uv run alembic upgrade head
```

4. Showing migration history

```bash
docker compose exec api uv run alembic history
```

5. Showing the latest migration

```bash
docker compose exec api uv run alembic heads
```

## Testing

1. Running tests

```bash
uv run pytest
```

2. Running tests with verbose output

```bash
uv run pytest -v
```