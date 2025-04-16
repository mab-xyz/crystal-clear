# Crystal-Clear API Backend

A FastAPI-based backend service for analyzing Ethereum smart contracts.

## Features

- Smart contract analysis
- Ethereum node integration
- RESTful API endpoints
- Comprehensive logging
- Environment-based configuration

## Prerequisites

- Python 3.12 or higher
- Docker and Docker Compose
- Access to an Ethereum node

## Environment Variables

Create a `.env` file in the backend directory with the following variables:

```env
# Ethereum Node Configuration
ETH_NODE_URL=http://localhost:8545

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/yourdb

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Optional: Logging Configuration
LOG_LEVEL=INFO
```

## Installation

### Using Docker

1. Build and run the container:
```bash
docker-compose up --build
```

### Local Development

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install poetry
poetry install
```

3. Run the development server:
```bash
uvicorn main:app --reload
```

## API Documentation

Once the server is running, you can access:
- Swagger UI documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## Project Structure

```
backend/
├── core/               # Core functionality
│   ├── config.py      # Configuration management
│   ├── logging.py     # Logging setup
│   └── exceptions.py  # Custom exceptions
├── routers/           # API routes
├── main.py           # Application entry point
├── Dockerfile        # Container configuration
└── requirements.txt  # Python dependencies
```

## Logging

The application uses loguru for logging. Log levels can be configured through the `LOG_LEVEL` environment variable.

## License

[Your License Here]
