FROM python:3.12-slim

WORKDIR /backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    curl \
    gnupg \
    ca-certificates \
    docker.io

# Install Node.js 23.x
RUN curl -fsSL https://deb.nodesource.com/setup_23.x -o nodesource_setup.sh && \
    bash nodesource_setup.sh && \
    apt-get update && \
    apt-get install -y nodejs && \
    rm nodesource_setup.sh

# Install sevm globally via npm
RUN npm install --global sevm

# Clean up apt cache
RUN rm -rf /var/lib/apt/lists/*

# Install Poetry to manage Python dependencies
RUN pip install --no-cache-dir poetry

# Copy dependency definitions first for better caching
COPY api/pyproject.toml api/poetry.lock ./

# Copying the dependency into the image
COPY crystal-clear/ /crystal-clear

# Copy your app files (needed before installing due to local path deps)
COPY api/ ./

# Install Python dependencies with Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-root

# Expose the API port
EXPOSE ${API_PORT}

# Start the application
CMD uvicorn api.main:app --host ${API_HOST} --port ${API_PORT}
