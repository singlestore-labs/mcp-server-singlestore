# Use an official Python runtime as a parent image
FROM python:3.11-alpine

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

# Expose the port the MCP server runs on
EXPOSE 8080

CMD ["python", "src/server.py", "start", "--protocol", "sse", "--port", "8080"]
