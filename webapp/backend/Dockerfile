FROM python:3.12-slim

# Create app directory
WORKDIR /backend

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*
    
# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port
EXPOSE ${API_PORT}

# Start app
CMD uvicorn main:app --host ${API_HOST} --port ${API_PORT}