# Use an official Python runtime as a parent image
FROM --platform=linux/amd64 python:3.11-alpine

# Set the working directory in the container
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Copy project files into the container
COPY pyproject.toml .
COPY requirements.txt .
COPY README.md .
COPY src/ ./src/
COPY uv.lock ./

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install --ignore-installed -r requirements.txt || true

# Install project using Hatchling build
RUN pip install hatchling \
    && pip install .

ENV SERVER_MODE=http

# Expose the port the MCP server runs on
EXPOSE 8000

CMD ["python", "src/server.py", "start", "--protocol", "http"]
