import json
import os
import sys
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

from app.main import app

client = TestClient(app)


def test_resume_weekly_command():
    print("1. Testing /resume command (current week)...")
    payload = {"text": "/resume"}
    resp = client.post("/analyze/text", json=payload)
    assert resp.status_code == 200, f"Failed: {resp.text}"

    data = resp.json()
    print("Response:")
    print(json.dumps(data, indent=2))

    assert data.get("is_summary") is True, "is_summary should be True"
    assert data.get("summary_text") is not None, "summary_text should not be None"
    assert "Bilan de la semaine" in data["summary_text"]
    assert "Moyennes journalières" in data["summary_text"]
    assert "Calories brûlées" in data["summary_text"]
    assert "Pas" in data["summary_text"]
    assert "Poids" in data["summary_text"]


def test_resume_yesterday_command():
    print("\n2. Testing /resume hier command...")
    payload = {"text": "/resume hier"}
    resp = client.post("/analyze/text", json=payload)
    assert resp.status_code == 200, f"Failed: {resp.text}"

    data = resp.json()
    assert data.get("is_summary") is True
    assert data.get("summary_text") is not None
    assert "Bilan du" in data["summary_text"]


def test_summary_endpoints():
    print("\n3. Testing GET /summary/week...")
    resp_week = client.get("/summary/week")
    assert resp_week.status_code == 200, f"Failed: {resp_week.text}"
    week_data = resp_week.json()
    assert "summary" in week_data
    assert "formatted_text" in week_data

    print("\n4. Testing GET /summary/daily...")
    resp_daily = client.get("/summary/daily")
    assert resp_daily.status_code == 200, f"Failed: {resp_daily.text}"
    daily_data = resp_daily.json()
    assert "daily" in daily_data
    assert "formatted_text" in daily_data


if __name__ == "__main__":
    test_resume_weekly_command()
    test_resume_yesterday_command()
    test_summary_endpoints()
