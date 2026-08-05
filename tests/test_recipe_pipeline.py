import requests
import json
from dotenv import load_dotenv
load_dotenv()
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

log_payload = {
    "analysis": {
        "repas": "snack",
        "total_kcal": 0,
        "total_proteines": 0,
        "total_glucides": 0,
        "total_lipides": 0,
        "is_creation_recette": True,
        "nom_recette": "Gâteau aux pommes Bot",
        "portions": 4,
        "aliments": [
            {
                "nom": "chocolat",
                "quantite_g": 200,
                "kcal": 1000,
                "proteines": 10,
                "glucides": 100,
                "lipides": 60,
                "is_recipe": False
            },
            {
                "nom": "pomme",
                "quantite_g": 300,
                "kcal": 150,
                "proteines": 0,
                "glucides": 40,
                "lipides": 0,
                "is_recipe": False
            }
        ]
    }
}

resp = client.post("/log", json=log_payload)
print(resp.status_code)
print(json.dumps(resp.json(), indent=2))
