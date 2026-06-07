import os
import time
import requests
import uuid
import json
import difflib
from datetime import datetime
from typing import Optional, List, Dict, Any

YAZIO_BASE_URL = "https://yzapi.yazio.com/v15"
YAZIO_CLIENT_ID = "1_4hiybetvfksgw40o0sog4s884kwc840wwso8go4k8c04goo4c"
YAZIO_CLIENT_SECRET = "6rok2m65xuskgkgogw40wkkk8sw0osg84s8cggsc4woos4s8o"

class YazioService:
    def __init__(self):
        self.email = os.getenv("YAZIO_EMAIL")
        self.password = os.getenv("YAZIO_PASSWORD")
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0
        self.cache_file = "/tmp/yazio_recipes_cache_v3.json"

    def authenticate(self) -> str:
        """Authenticate with Yazio and return the access token."""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        if not self.email or not self.password:
            raise ValueError("YAZIO_EMAIL and YAZIO_PASSWORD must be set in the environment.")
            
        response = requests.post(
            f"{YAZIO_BASE_URL}/oauth/token",
            json={
                "client_id": YAZIO_CLIENT_ID,
                "client_secret": YAZIO_CLIENT_SECRET,
                "username": self.email,
                "password": self.password,
                "grant_type": "password"
            }
        )
        
        if not response.ok:
            raise Exception(f"Failed to authenticate with Yazio: {response.text}")
            
        data = response.json()
        self.access_token = data["access_token"]
        self.token_expires_at = time.time() + data.get("expires_in", 3600)
        
        return self.access_token

    def search_products(self, query: str) -> List[Dict[str, Any]]:
        """Search for products in Yazio."""
        token = self.authenticate()
        
        params = {
            "query": query,
            "sex": "male",
            "countries": "FR,US",
            "locales": "fr_FR,en_US"
        }
        
        response = requests.get(
            f"{YAZIO_BASE_URL}/products/search",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if not response.ok:
            raise Exception(f"Failed to search products: {response.text}")
            
        return response.json()

    def _fetch_and_cache_recipes(self) -> Dict[str, str]:
        """Fetch all user recipes from Yazio and save them to a local JSON file."""
        token = self.authenticate()
        
        res = requests.get(f"{YAZIO_BASE_URL}/user/recipes", headers={"Authorization": f"Bearer {token}"})
        if not res.ok:
            return {}
            
        recipe_ids = res.json()
        recipes_map = {}
        
        for rid in recipe_ids:
            r = requests.get(f"{YAZIO_BASE_URL}/recipes/{rid}", headers={"Authorization": f"Bearer {token}"})
            if r.ok:
                data = r.json()
                name = data.get("name")
                if name:
                    total_weight = 0
                    for s in data.get("servings", []):
                        amt = s.get("amount", 0) or 0
                        total_weight += amt
                    
                    if total_weight <= 0:
                        total_weight = 400
                        
                    recipes_map[name.lower()] = {
                        "recipe_id": rid,
                        "total_weight": total_weight,
                        "portion_count": data.get("portion_count", 1)
                    }
                    
        with open(self.cache_file, "w") as f:
            json.dump(recipes_map, f)
            
        return recipes_map

    def search_recipe(self, query: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Search for a personal recipe in the local cache using fuzzy matching.
        If no matches are found, it triggers a cache refresh and tries again.
        Returns a dictionary containing recipe details or None if not found.
        """
        recipes_map = {}
        
        if not force_refresh and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    recipes_map = json.load(f)
            except Exception:
                pass
                
        if not recipes_map or force_refresh:
            recipes_map = self._fetch_and_cache_recipes()
            
        if not recipes_map:
            return None
            
        query_lower = query.lower()
        matches = difflib.get_close_matches(query_lower, recipes_map.keys(), n=1, cutoff=0.5)
        
        if matches:
            best_match = matches[0]
            recipe_data = recipes_map[best_match]
            return {
                "name": best_match, 
                "recipe_id": recipe_data["recipe_id"],
                "total_weight": recipe_data["total_weight"],
                "portion_count": recipe_data["portion_count"]
            }
            
        if not force_refresh:
            return self.search_recipe(query, force_refresh=True)
            
        return None

    def log_food(self, product_id: str, amount: float, serving: str, serving_quantity: float, daytime: str = "lunch") -> None:
        """
        Log a food item to Yazio.
        daytime can be 'breakfast', 'lunch', 'snack', 'dinner'.
        """
        token = self.authenticate()
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        payload = {
            "recipe_portions": [],
            "simple_products": [],
            "products": [
                {
                    "id": str(uuid.uuid4()),
                    "product_id": product_id,
                    "date": date_str,
                    "daytime": daytime,
                    "amount": amount,
                    "serving": serving,
                    "serving_quantity": serving_quantity
                }
            ]
        }
        
        response = requests.post(
            f"{YAZIO_BASE_URL}/user/consumed-items",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if not response.ok:
            raise Exception(f"Failed to log food: {response.text}")

    def log_recipe(self, recipe_id: str, portion_count: float, daytime: str = "lunch") -> None:
        """Log a personal recipe to Yazio."""
        token = self.authenticate()
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        payload = {
            "recipe_portions": [
                {
                    "id": str(uuid.uuid4()),
                    "recipe_id": recipe_id,
                    "date": date_str,
                    "daytime": daytime,
                    "portion_count": portion_count
                }
            ],
            "simple_products": [],
            "products": []
        }
        
        response = requests.post(
            f"{YAZIO_BASE_URL}/user/consumed-items",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if not response.ok:
            raise Exception(f"Failed to log recipe: {response.text}")

    def create_recipe(self, name: str, portion_count: int, aliments: list) -> dict:
        """Create a new recipe in Yazio."""
        token = self.authenticate()
        
        recipe_nutrients = {
            "energy.energy": 0.0,
            "nutrient.fat": 0.0,
            "nutrient.protein": 0.0,
            "nutrient.carb": 0.0
        }
        
        servings = []
        
        for aliment in aliments:
            search_res = self.search_products(aliment.nom)
            if not search_res:
                continue
                
            best_match = search_res[0]
            product_id = best_match["product_id"]
            nutrients = best_match.get("nutrients", {})
            
            for k in recipe_nutrients.keys():
                if k in nutrients:
                    recipe_nutrients[k] += nutrients[k] * aliment.quantite_g
                    
            servings.append({
                "name": best_match["name"],
                "amount": float(aliment.quantite_g),
                "serving": "gram",
                "serving_quantity": float(aliment.quantite_g),
                "base_unit": "g",
                "product_id": product_id
            })
            
        if len(servings) < 2:
            raise Exception("A Yazio recipe must contain at least 2 valid ingredients. We found: " + str([s["name"] for s in servings]))
            
        payload = {
            "id": str(uuid.uuid4()),
            "name": name or "Recette personnalisée",
            "portion_count": portion_count or 1,
            "nutrients": recipe_nutrients,
            "servings": servings
        }
        
        response = requests.post(
            f"{YAZIO_BASE_URL}/user/recipes",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if not response.ok:
            raise Exception(f"Failed to create recipe: {response.text}")
            
        # Invalidate cache
        if os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
            except Exception:
                pass
                
        return recipe_nutrients

