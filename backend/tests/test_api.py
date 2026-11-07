"""Integration tests for FastAPI endpoints."""

import pytest

# Skip if database dependencies are not in local host python
sqlalchemy = pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Verity API"
    assert "version" in data


def test_health_check_endpoint():
    response = client.get("/api/system/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "uptime_seconds" in data


def test_document_validation_file_extension():
    files = {"file": ("malicious.exe", b"invalid binary", "application/octet-stream")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json().get("error", "")


def test_research_query_validation():
    response = client.post("/api/research/query", json={"query": ""})
    assert response.status_code == 422
