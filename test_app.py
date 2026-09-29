import os

os.environ["DEMO_MODE"] = "false"
os.environ["ADMIN_TOKEN"] = "fitbuddy-admin"
os.environ["DATABASE_URL"] = "sqlite:///./data/test_fitbuddy.db"

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert "FitBuddy" in response.text


def test_generate_api_demo_mode():
    response = client.post(
        "/api/generate-workout",
        json={
            "username": "Test User",
            "user_id": "TEST001",
            "age": 20,
            "weight_kg": 60,
            "goal": "general wellness",
            "intensity": "medium",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["workout_plan"]["days"]) == 7
    assert "nutrition_tip" in body


def test_feedback_api_demo_mode():
    response = client.post(
        "/api/submit-feedback",
        json={
            "user_id": "TEST001",
            "feedback": "Please make the first day easier.",
        },
    )
    assert response.status_code == 200
    assert len(response.json()["updated_plan"]["days"]) == 7
