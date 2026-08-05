import json
from dotenv import load_dotenv
load_dotenv()
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("1. Tester la route /log pour la création d'une équivalence")
payload = {
    "analysis": {
        "repas": "snack",
        "aliments": [],
        "total_kcal": 0,
        "total_proteines": 0,
        "total_glucides": 0,
        "total_lipides": 0,
        "is_creation_equivalence": True,
        "equivalence_key": "1 tranche de jambon blanc",
        "equivalence_value": "45g"
    }
}

resp = client.post("/log", json=payload)
print(resp.status_code)
print(json.dumps(resp.json(), indent=2))

print("\n2. Vérification du fichier custom_weights.json")
weights_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "data", "custom_weights.json")
with open(weights_file, "r") as f:
    print(f.read())
