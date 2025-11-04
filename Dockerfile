FROM python:3.11-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


# Add ARGs for build-time configuration with defaults
ARG TRANSPORT=streamable-http
ARG HOST=0.0.0.0
ARG PORT=8010

# Set ENV vars from ARGs to be available at runtime
ENV TRANSPORT=${TRANSPORT}
ENV HOST=${HOST}
ENV PORT=${PORT}


# Copy the project into the image
ADD . /app

# Sync the project into a new environment, asserting the lockfile is up to date
WORKDIR /app

RUN uv sync --locked --no-cache

# Expose the port the MCP server runs on
EXPOSE ${PORT}

# Use the environment variables in the CMD instruction
CMD uv run src/main.py start --transport ${TRANSPORT} --host ${HOST}
