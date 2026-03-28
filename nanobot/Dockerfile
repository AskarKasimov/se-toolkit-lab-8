# Nanobot Dockerfile - multi-stage build with uv
# Pattern adapted from backend/Dockerfile and qwen-code-api/Dockerfile

# ---
# Stage 1: build the application in the `/app` directory.
# ---

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}astral/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Disable Python downloads - use the system interpreter across both images.
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy workspace root files
COPY --from=workspace pyproject.toml uv.lock /app/

# Copy nanobot package (context is ./nanobot)
COPY pyproject.toml /app/nanobot/pyproject.toml
COPY . /app/nanobot/

# Copy mcp-lms package for workspace dependency resolution
COPY --from=workspace mcp/ /app/mcp/

# Copy nanobot-websocket-channel packages for workspace dependencies
COPY --from=workspace nanobot-websocket-channel/ /app/nanobot-websocket-channel/

# Sync all dependencies including workspace members
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package nanobot

# ---
# Stage 2: use a final image without uv
# ---

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}python:3.14.2-slim-bookworm

# Accept build args for runtime user configuration
# These should match the HOST_UID/HOST_GID from docker-compose for bind-mount compatibility
ARG APP_UID=999
ARG APP_GID=999

# Set environment variables for Python and application
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Make sure we use UTF-8 encoding
ENV LANG=C.UTF-8

# Install gosu for dropping privileges
RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/*

# Create the non-root user with configurable UID/GID
RUN groupadd --system --gid ${APP_GID} nonroot \
    && useradd --system --gid ${APP_GID} --uid ${APP_UID} --create-home nonroot

# Copy the application from the builder
COPY --from=builder --chown=nonroot:nonroot /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Use the non-root user to run our application
USER nonroot

# Use /app as the working directory
WORKDIR /app

# Run the entrypoint which resolves config and launches nanobot gateway
CMD ["python", "/app/nanobot/entrypoint.py"]
