from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sample_medical_schools_endpoint_strict_mode():
    response = client.get("/medical-schools/africa?sample=true&strict_only=true&min_confidence=medium")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["count"] == 2
    assert all(row["is_medical_school"] for row in payload["results"])


def test_sample_medical_schools_endpoint_broad_mode():
    response = client.get("/medical-schools/africa?sample=true&strict_only=false&min_confidence=low")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["count"] == 3
    assert payload["meta"]["category_counts"]["related_medical_institution"] == 1
