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

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app files
COPY . .

# Expose the API port
EXPOSE ${API_PORT}

# Start the application
CMD uvicorn main:app --host ${API_HOST} --port ${API_PORT}
