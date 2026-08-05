import json
from dotenv import load_dotenv
load_dotenv()
from app.services.yazio_service import YazioService

y = YazioService()
res = y.search_products("pomme")
print(json.dumps(res[0], indent=2))
