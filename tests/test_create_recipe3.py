import os
import requests
import json
import uuid
from dotenv import load_dotenv

load_dotenv()

YAZIO_BASE_URL = "https://yzapi.yazio.com/v15"
YAZIO_CLIENT_ID = "1_4hiybetvfksgw40o0sog4s884kwc840wwso8go4k8c04goo4c"
YAZIO_CLIENT_SECRET = "6rok2m65xuskgkgogw40wkkk8sw0osg84s8cggsc4woos4s8o"

email = os.getenv("YAZIO_EMAIL")
password = os.getenv("YAZIO_PASSWORD")

# Authenticate
response = requests.post(
    f"{YAZIO_BASE_URL}/oauth/token",
    json={
        "client_id": YAZIO_CLIENT_ID,
        "client_secret": YAZIO_CLIENT_SECRET,
        "username": email,
        "password": password,
        "grant_type": "password"
    }
)
token = response.json()["access_token"]

new_id = str(uuid.uuid4())
payload = {
  "id": new_id,
  "name": "Bot API Test Recipe V4",
  "portion_count": 1,
  "nutrients": {
    "energy.energy": 100,
    "nutrient.fat": 1,
    "nutrient.protein": 1,
    "nutrient.carb": 1
  },
  "servings": [
    {
      "name": "Pomme",
      "amount": 100.0,
      "serving": "gram",
      "serving_quantity": 100.0,
      "base_unit": "g",
      "product_id": "9d76debe-becf-11e6-8c48-e0071b8a8723"
    },
    {
      "name": "Poire",
      "amount": 100.0,
      "serving": "gram",
      "serving_quantity": 100.0,
      "base_unit": "g",
      "product_id": "a6c285f4-becf-11e6-8a95-e0071b8a8723"
    }
  ]
}

res = requests.put(
    f"{YAZIO_BASE_URL}/recipes/{new_id}",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=payload
)
print(res.status_code)
print(res.text)

# Check if it was created
r = requests.get(f"{YAZIO_BASE_URL}/recipes/{new_id}", headers={"Authorization": f"Bearer {token}"})
if r.ok:
    print("Recipe found!")
else:
    print("Recipe NOT found:", r.status_code)
