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

# Install Node.js 24.x
RUN curl -fsSL https://deb.nodesource.com/setup_24.x -o nodesource_setup.sh && \
    bash nodesource_setup.sh && \
    apt-get update && \
    apt-get install -y nodejs && \
    rm nodesource_setup.sh

# Install sevm globally via npm
RUN npm install --global sevm

# Add npm global bin to PATH
# ENV PATH="/usr/local/lib/node_modules/.bin:${PATH}"

# Verify sevm is accessible
# RUN which sevm && sevm --version || echo "sevm installation check"

# Clean up apt cache
RUN rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Install Python dependencies from pyproject.toml
COPY pyproject.toml .
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main

# Copy your app files
COPY . .

# Install the bundled crystal-clear SDK
RUN pip install --no-cache-dir -e ./crystal-clear

# Expose the API port
EXPOSE ${API_PORT}

# Start the application
CMD uvicorn src.api.main:app --host ${API_HOST} --port ${API_PORT}
