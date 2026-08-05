import os
import requests
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

res = requests.get(f"{YAZIO_BASE_URL}/user/recipes", headers={"Authorization": f"Bearer {token}"})
recipe_ids = res.json()

for rid in recipe_ids:
    r = requests.get(f"{YAZIO_BASE_URL}/recipes/{rid}", headers={"Authorization": f"Bearer {token}"})
    if r.ok:
        data = r.json()
        name = data.get('name')
        if "Test" in name or "Poivronnade" in name or "Bot" in name:
            print(f"FOUND: {name} (ID: {rid})")
