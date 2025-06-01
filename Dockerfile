FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, asserting the lockfile is up to date
WORKDIR /app
RUN uv sync --locked

# Expose the port the MCP server runs on
EXPOSE 8000

CMD ["uv", "run", "src/main.py", "start", "--transport", "sse"]
