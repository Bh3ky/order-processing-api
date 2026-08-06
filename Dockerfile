# Start from the official Python runtime image with a slim variant for smaller size
FROM python:3.13.7-slim

# Set the working directory in the container.
WORKDIR /app

# Copy dependency metadata files
# Docker can cache dependency installation until these files change.
COPY pyproject.toml uv.lock ./

# C
COPY --from=ghcr.io/astral-sh/uv:0.8.8 /uv /uvx /bin/ 
