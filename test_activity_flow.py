import json
import requests
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

from app.main import app
from app.services.yazio_service import YazioService

client = TestClient(app)


def test_activity_flow():
    # 1. Analyze text query requesting activity tracking
    print("Testing initial text analysis for activity...")
    analyze_payload = {
        "text": "1h30 d'entrainement de tennis",
        "local_time": "2026-08-04T12:30:00+02:00"
    }
    resp_analyze = client.post("/analyze/text", json=analyze_payload)
    print(f"Analyze Status Code: {resp_analyze.status_code}")
    assert resp_analyze.status_code == 200, f"Analysis failed: {resp_analyze.text}"

    analysis_data = resp_analyze.json()
    print("Initial Analysis Response JSON:")
    print(json.dumps(analysis_data, indent=2))

    assert analysis_data.get("is_activity") is True, "is_activity should be True"
    assert "tennis" in analysis_data.get("nom_activite", "").lower(), "Activity name should include 'tennis'"
    assert analysis_data.get("duree_minutes") == 90, "duree_minutes should be 90"
    assert analysis_data.get("calories_brules") is not None and analysis_data.get("calories_brules") > 0, "Calories burned should be set"
    assert not analysis_data.get("aliments"), "Aliments list should be empty"

    # 2. Refine analysis by simulating a reply answering questions / correcting
    print("\nTesting activity correction...")
    correction_payload = {
        "original_analysis": analysis_data,
        "correction": "C'était en fait 2h d'entraînement intense",
        "local_time": "2026-08-04T12:35:00+02:00"
    }
    resp_correction = client.post("/analyze/correction", json=correction_payload)
    print(f"Correction Status Code: {resp_correction.status_code}")
    assert resp_correction.status_code == 200, f"Correction failed: {resp_correction.text}"

    corrected_data = resp_correction.json()
    print("Corrected Analysis Response JSON:")
    print(json.dumps(corrected_data, indent=2))

    assert corrected_data.get("is_activity") is True, "Should remain an activity"
    assert corrected_data.get("duree_minutes") == 120, "Duration should be updated to 120 minutes (2h)"
    assert corrected_data.get("calories_brules") > analysis_data.get("calories_brules"), "Calories burned should be higher for longer and more intense activity"

    # 3. Log the final corrected activity
    print("\nTesting log endpoint for final activity...")
    log_payload = {
        "analysis": corrected_data
    }
    resp_log = client.post("/log", json=log_payload)
    print(f"Log Status Code: {resp_log.status_code}")
    print("Log Response JSON:")
    print(json.dumps(resp_log.json(), indent=2))
    assert resp_log.status_code == 200, f"Logging failed: {resp_log.text}"

    # 4. Verify in Yazio and clean up
    print("\nVerifying activity in Yazio...")
    yazio = YazioService()
    token = yazio.authenticate()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    r = requests.get("https://yzapi.yazio.com/v15/user/exercises?date=2026-08-04", headers=headers)
    assert r.status_code == 200, f"Failed to get Yazio exercises: {r.text}"

    state = r.json()
    custom_trainings = state.get("custom_training", [])

    # Check if our logged activity is present
    found = False
    matching_ids = []
    for item in custom_trainings:
        if "tennis" in item.get("name", "").lower() and item.get("duration") == 120:
            found = True
            matching_ids.append(item["id"])

    assert found, f"Activity not found in Yazio exercises. Exercises: {custom_trainings}"
    print(f"Successfully verified activity in Yazio! Matching IDs to clean up: {matching_ids}")

    # Delete the logged activity to keep user diary clean
    if matching_ids:
        print(f"Cleaning up logged exercise IDs: {matching_ids}")
        yazio.delete_activities(matching_ids)

        # Verify deletion
        r = requests.get("https://yzapi.yazio.com/v15/user/exercises?date=2026-08-04", headers=headers)
        state_after = r.json()
        assert not any(item["id"] in matching_ids for item in state_after.get("custom_training", [])), "Activity should have been deleted"
        print("Cleanup successful!")

    print("\nTest completed successfully!")


if __name__ == "__main__":
    test_activity_flow()
