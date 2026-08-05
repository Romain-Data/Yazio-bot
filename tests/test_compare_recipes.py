import os
import requests
import json
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

# fetch the old one
r_old = requests.get(f"{YAZIO_BASE_URL}/recipes/ad9e41d9-289b-48f7-825d-cfdd869f5cb1", headers={"Authorization": f"Bearer {token}"})

# fetch the newly created one (Bot API Test Recipe)
r_new = requests.get(f"{YAZIO_BASE_URL}/recipes/d3dc28f5-8034-46df-9bb3-c4829f387482", headers={"Authorization": f"Bearer {token}"})

print("OLD RECIPE:")
print(json.dumps(r_old.json(), indent=2))
print("\nNEW RECIPE:")
print(json.dumps(r_new.json(), indent=2))

