import json
import os
from dotenv import load_dotenv
from app.services.mammouth_service import MammouthService

load_dotenv()

mammouth_service = MammouthService()
resp = mammouth_service.analyze_text("Nouvelle équivalence : 1 tortilla old el paso 41g")
print(resp.model_dump_json(indent=2))
