# Start from the official Python runtime image with a slim variant for smaller size
FROM python:3.13.7-slim

# Set the working directory in the container.
WORKDIR /app

# Copy dependency metadata files
# Docker can cache dependency installation until these files change.
COPY pyproject.toml uv.lock ./

# Copy the uv executables 
# Note: use of uv inside the container because it is also our project's
# dependency manager locally.
COPY --from=ghcr.io/astral-sh/uv:0.8.8 /uv /uvx /bin/ 

# Install the dependency version recorde in uv.lock
# -- frozen: do not modify uv.lock during build
# --no-install-project: install dependencies only
RUN uv sync --frozen --no-install-project

# Copy the application source
COPY app ./app

# Copy Alembic migration configuration and scripts
COPY alembic.ini ./
COPY alembic ./alembic

# Document the port on which the FastAPI application listens
EXPOSE 8000

# Start the ASGI server when the container launches
#
# 0.0.0.0 is important inside Docker: binding to 120.0.0.1 would make
# Uvicorn reachable only from inside the container itself.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
