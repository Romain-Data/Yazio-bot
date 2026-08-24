import json
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

from app.main import app

client = TestClient(app)


def test_estimation_flow():
    # 1. Analyze text query requesting an estimation
    print("Testing initial text analysis for estimation...")
    analyze_payload = {
        "text": "Estime mon assiette de couscous royal au resto ce midi",
        "local_time": "2026-08-04T12:30:00+02:00"
    }
    resp_analyze = client.post("/analyze/text", json=analyze_payload)
    print(f"Analyze Status Code: {resp_analyze.status_code}")
    assert resp_analyze.status_code == 200, f"Analysis failed: {resp_analyze.text}"

    analysis_data = resp_analyze.json()
    print("Initial Analysis Response JSON:")
    print(json.dumps(analysis_data, indent=2))

    assert analysis_data.get("is_estimation") is True, "is_estimation should be True"
    assert analysis_data.get("nom_estimation") is not None, "nom_estimation should not be None"
    assert len(analysis_data.get("aliments", [])) == 1, "Should have exactly one virtual aliment"
    assert len(analysis_data.get("questions", [])) > 0, "Should contain refining questions"

    # 2. Refine analysis by simulating a reply answering the questions
    print("\nTesting correction (answering questions)...")
    correction_payload = {
        "original_analysis": analysis_data,
        "correction": "C'était une grande portion avec 2 merguez, pas de sauce huileuse",
        "local_time": "2026-08-04T12:35:00+02:00"
    }
    resp_correction = client.post("/analyze/correction", json=correction_payload)
    print(f"Correction Status Code: {resp_correction.status_code}")
    assert resp_correction.status_code == 200, f"Correction failed: {resp_correction.text}"

    corrected_data = resp_correction.json()
    print("Corrected Analysis Response JSON:")
    print(json.dumps(corrected_data, indent=2))

    assert corrected_data.get("is_estimation") is True, "Should remain an estimation"
    # Calories/macros should have adjusted
    print(f"Original kcal: {analysis_data['total_kcal']} -> Corrected kcal: {corrected_data['total_kcal']}")

    # 3. Log the final corrected estimation
    print("\nTesting log endpoint for final estimation...")
    log_payload = {
        "analysis": corrected_data
    }
    resp_log = client.post("/log", json=log_payload)
    print(f"Log Status Code: {resp_log.status_code}")
    print("Log Response JSON:")
    print(json.dumps(resp_log.json(), indent=2))
    assert resp_log.status_code == 200, f"Logging failed: {resp_log.text}"

    print("\nTest completed successfully!")


def test_estimation_meal_override():
    # 1. Analyze text query requesting an estimation with an explicit meal type in text
    print("\nTesting text analysis with explicit meal override...")
    analyze_payload = {
        "text": "Estime mon dîner: une pizza marguerita au resto",
        "local_time": "2026-08-04T12:30:00+02:00"  # This hour would normally map to lunch
    }
    resp_analyze = client.post("/analyze/text", json=analyze_payload)
    assert resp_analyze.status_code == 200, f"Analysis failed: {resp_analyze.text}"

    analysis_data = resp_analyze.json()
    print("Meal type from response (expected: dinner):", analysis_data.get("repas"))
    assert analysis_data.get("repas") == "dinner", "repas should be 'dinner' due to text override"

    # 2. Refine analysis with a correction changing the meal type
    print("\nTesting correction with explicit meal override...")
    correction_payload = {
        "original_analysis": analysis_data,
        "correction": "Finalement c'était plutôt mon snack de l'après-midi",
        "local_time": "2026-08-04T12:35:00+02:00"
    }
    resp_correction = client.post("/analyze/correction", json=correction_payload)
    assert resp_correction.status_code == 200, f"Correction failed: {resp_correction.text}"

    corrected_data = resp_correction.json()
    print("Corrected meal type from response (expected: snack):", corrected_data.get("repas"))
    assert corrected_data.get("repas") == "snack", "repas should be 'snack' due to correction override"


if __name__ == "__main__":
    test_estimation_flow()
    test_estimation_meal_override()
