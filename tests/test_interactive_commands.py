import json
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

from app.main import app

client = TestClient(app)


def test_interactive_activity_command():
    print("1. Testing standalone /activite command (interactive prompt)...")
    payload = {"text": "/activite"}
    resp = client.post("/analyze/text", json=payload)
    assert resp.status_code == 200, f"Failed: {resp.text}"

    data = resp.json()
    print("Command response:")
    print(json.dumps(data, indent=2))

    assert data.get("is_prompt") is True, "is_prompt should be True"
    assert data.get("is_activity") is True, "is_activity should be True"
    assert len(data.get("questions", [])) == 1, "Should have 1 question"
    assert "activité" in data["questions"][0].lower(), "Question should relate to activity"
    assert data.get("nom_activite") is None, "Should not have activity name yet"

    # Now simulate the reply answering the prompt
    print("\n2. Simulating user reply answering the prompt...")
    reply_payload = {
        "original_analysis": data,
        "correction": "1h30 de tennis intense",
        "local_time": "2026-08-04T12:00:00+02:00",
    }
    resp_reply = client.post("/analyze/correction", json=reply_payload)
    assert resp_reply.status_code == 200, f"Failed: {resp_reply.text}"

    replied_data = resp_reply.json()
    print("Reply response:")
    print(json.dumps(replied_data, indent=2))

    assert replied_data.get("is_prompt") is False, "is_prompt should be False after reply"
    assert replied_data.get("is_activity") is True, "Should remain an activity"
    assert "tennis" in replied_data.get("nom_activite", "").lower()
    assert replied_data.get("duree_minutes") == 90
    assert replied_data.get("calories_brules") is not None and replied_data.get("calories_brules") > 0


def test_interactive_estimation_command():
    print("\n3. Testing standalone /estimation command...")
    payload = {"text": "/estimation"}
    resp = client.post("/analyze/text", json=payload)
    assert resp.status_code == 200, f"Failed: {resp.text}"

    data = resp.json()
    print("Command response:")
    print(json.dumps(data, indent=2))

    assert data.get("is_prompt") is True, "is_prompt should be True"
    assert data.get("is_estimation") is True, "is_estimation should be True"
    assert len(data.get("questions", [])) == 1
    assert "estimer" in data["questions"][0].lower()

    # Now simulate user reply
    print("\n4. Simulating user reply answering the prompt...")
    reply_payload = {
        "original_analysis": data,
        "correction": "un plat de pâtes bolognaises au resto",
        "local_time": "2026-08-04T13:00:00+02:00",
    }
    resp_reply = client.post("/analyze/correction", json=reply_payload)
    assert resp_reply.status_code == 200, f"Failed: {resp_reply.text}"

    replied_data = resp_reply.json()
    print("Reply response:")
    print(json.dumps(replied_data, indent=2))

    assert replied_data.get("is_prompt") is False
    assert replied_data.get("is_estimation") is True
    assert replied_data.get("total_kcal") > 0


if __name__ == "__main__":
    test_interactive_activity_command()
    test_interactive_estimation_command()
