from fastapi.testclient import TestClient

from src.api.main import app  # Assuming your FastAPI app is defined in src.main

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to the Crystal-Clear API!",
        "docs": "/docs",
        "redoc": "/redoc",
    }
