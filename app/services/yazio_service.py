import difflib
import json
import os
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid
import requests


YAZIO_BASE_URL = "https://yzapi.yazio.com/v15"

# Yazio Official Client App Credentials (Non-Personal)
YAZIO_CLIENT_ID = "1_4hiybetvfksgw40o0sog4s884kwc840wwso8go4k8c04goo4c"
YAZIO_CLIENT_SECRET = "6rok2m65xuskgkgogw40wkkk8sw0osg84s8cggsc4woos4s8o"


class YazioService:
    def __init__(self):
        self.email = os.getenv("YAZIO_EMAIL")
        self.password = os.getenv("YAZIO_PASSWORD")
        self.access_token: str | None = None
        self.token_expires_at: float = 0
        self.cache_file = "/tmp/yazio_recipes_cache_v3.json"
        self.products_cache_file = "/tmp/yazio_products_cache_v1.json"
        self._products_memory_cache: Dict[str, Any] = {}
        self._load_products_cache()

    def authenticate(self, force: bool = False) -> str:
        """Authenticate with Yazio and return the access token."""
        if not force and self.access_token and time.time() < self.token_expires_at:
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
            },
            timeout=15
        )

        if not response.ok:
            raise Exception(f"Failed to authenticate with Yazio: {response.text}")

        data = response.json()
        self.access_token = data["access_token"]
        self.token_expires_at = time.time() + data.get("expires_in", 3600)

        return self.access_token

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Execute an HTTP request to Yazio API with automatic retry on 401 Unauthorized."""
        token = self.authenticate()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        if "timeout" not in kwargs:
            kwargs["timeout"] = 15

        response = requests.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401 or (not response.ok and "Invalid credentials" in response.text):
            token = self.authenticate(force=True)
            headers["Authorization"] = f"Bearer {token}"
            response = requests.request(method, url, headers=headers, **kwargs)

        return response

    def search_products(self, query: str) -> List[Dict[str, Any]]:
        """Search for products in Yazio."""
        params = {
            "query": query,
            "sex": "male",
            "countries": "FR,US",
            "locales": "fr_FR,en_US"
        }

        response = self._request(
            "GET",
            f"{YAZIO_BASE_URL}/products/search",
            params=params
        )

        if not response.ok:
            raise Exception(f"Failed to search products: {response.text}")

        return response.json()

    def _fetch_and_cache_recipes(self) -> Dict[str, str]:
        """Fetch all user recipes from Yazio and save them to a local JSON file."""
        res = self._request("GET", f"{YAZIO_BASE_URL}/user/recipes")
        if not res.ok:
            return {}

        recipe_ids = res.json()
        recipes_map = {}

        for rid in recipe_ids:
            r = self._request("GET", f"{YAZIO_BASE_URL}/recipes/{rid}")
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

    def search_recipe(self, query: str, force_refresh: bool = False) -> Dict[str, Any] | None:
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

        response = self._request(
            "POST",
            f"{YAZIO_BASE_URL}/user/consumed-items",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if not response.ok:
            raise Exception(f"Failed to log food: {response.text}")

    def log_recipe(self, recipe_id: str, portion_count: float, daytime: str = "lunch") -> None:
        """Log a personal recipe to Yazio."""
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

        response = self._request(
            "POST",
            f"{YAZIO_BASE_URL}/user/consumed-items",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if not response.ok:
            raise Exception(f"Failed to log recipe: {response.text}")

    def create_recipe(self, name: str, portion_count: int, aliments: list) -> dict:
        """Create a new recipe in Yazio."""
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

        response = self._request(
            "POST",
            f"{YAZIO_BASE_URL}/user/recipes",
            json=payload,
            headers={"Content-Type": "application/json"}
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

    def log_simple_product(self, name: str, kcal: float, protein: float, carb: float, fat: float, daytime: str = "lunch") -> None:
        """Log a simple product (quick add) to Yazio."""
        date_str = datetime.now().strftime("%Y-%m-%d")

        payload = {
            "products": [],
            "recipe_portions": [],
            "simple_products": [
                {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "nutrients": {
                        "energy.energy": round(kcal),
                        "nutrient.protein": round(protein, 1),
                        "nutrient.carb": round(carb, 1),
                        "nutrient.fat": round(fat, 1)
                    },
                    "date": date_str,
                    "daytime": daytime
                }
            ]
        }

        response = self._request(
            "POST",
            f"{YAZIO_BASE_URL}/user/consumed-items",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if not response.ok:
            raise Exception(f"Failed to log simple product: {response.text}")

    def log_activity(self, name: str, kcal: float, duration_minutes: int) -> dict:
        """Log a custom physical activity to Yazio."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "custom_training": [
                {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "energy": float(kcal),
                    "duration": int(duration_minutes),  # duration is in minutes
                    "date": now_str,
                    "source": "manual",
                    "gateway": "manual"
                }
            ],
            "training": []
        }

        response = self._request(
            "POST",
            f"{YAZIO_BASE_URL}/user/exercises",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        if not response.ok:
            raise Exception(f"Failed to log activity: {response.text}")

        return {
            "id": payload["custom_training"][0]["id"],
            "name": name,
            "kcal": kcal,
            "duration": duration_minutes
        }

    def delete_activities(self, ids: List[str]) -> None:
        """Delete exercises/activities from Yazio diary using their IDs."""
        response = self._request(
            "DELETE",
            f"{YAZIO_BASE_URL}/user/exercises/trainings",
            json=ids,
            headers={"Content-Type": "application/json"}
        )

        if not response.ok:
            raise Exception(f"Failed to delete exercises: {response.text}")

    def _load_products_cache(self) -> None:
        if os.path.exists(self.products_cache_file):
            try:
                with open(self.products_cache_file, "r") as f:
                    self._products_memory_cache = json.load(f)
            except Exception:
                self._products_memory_cache = {}

    def _save_products_cache(self) -> None:
        try:
            with open(self.products_cache_file, "w") as f:
                json.dump(self._products_memory_cache, f)
        except Exception:
            pass

    def get_product(self, product_id: str) -> Dict[str, Any] | None:
        """Fetch product details by ID, using local memory and file cache."""
        if product_id in self._products_memory_cache:
            return self._products_memory_cache[product_id]

        res = self._request("GET", f"{YAZIO_BASE_URL}/products/{product_id}")
        if res.ok:
            data = res.json()
            self._products_memory_cache[product_id] = {
                "name": data.get("name", "Aliment"),
                "nutrients": data.get("nutrients", {})
            }
            self._save_products_cache()
            return self._products_memory_cache[product_id]

        return None

    def get_recipe(self, recipe_id: str) -> Dict[str, Any] | None:
        """Fetch recipe details by ID."""
        res = self._request("GET", f"{YAZIO_BASE_URL}/recipes/{recipe_id}")
        if res.ok:
            return res.json()
        return None

    def get_bodyvalues(self, date_str: str) -> Dict[str, Any]:
        """Fetch user body measurements (e.g. weight) for a specific date (YYYY-MM-DD)."""
        response = self._request(
            "GET",
            f"{YAZIO_BASE_URL}/user/bodyvalues",
            params={"date": date_str}
        )
        if not response.ok:
            return {}
        return response.json()

    def get_exercises(self, date_str: str) -> Dict[str, Any]:
        """Fetch user exercises, activity, and steps for a specific date (YYYY-MM-DD)."""
        response = self._request(
            "GET",
            f"{YAZIO_BASE_URL}/user/exercises",
            params={"date": date_str}
        )
        if not response.ok:
            return {}
        return response.json()

    def get_consumed_items(self, date_str: str) -> Dict[str, Any]:
        """Fetch consumed items for a specific date (YYYY-MM-DD)."""
        response = self._request(
            "GET",
            f"{YAZIO_BASE_URL}/user/consumed-items",
            params={"date": date_str}
        )
        if not response.ok:
            raise Exception(f"Failed to get consumed items for {date_str}: {response.text}")
        return response.json()

    def get_daily_summary(self, date_str: str) -> Dict[str, Any]:
        """Calculates and aggregates nutritional, weight and activity summary for a specific date."""
        consumed = self.get_consumed_items(date_str)
        products = consumed.get("products", [])
        simple_products = consumed.get("simple_products", [])
        recipe_portions = consumed.get("recipe_portions", [])

        day_kcal = 0.0
        day_protein = 0.0
        day_carb = 0.0
        day_fat = 0.0

        meals_dict = {
            "breakfast": {"label": "Petit-déjeuner", "items": [], "kcal": 0.0},
            "lunch": {"label": "Déjeuner", "items": [], "kcal": 0.0},
            "snack": {"label": "Collation", "items": [], "kcal": 0.0},
            "dinner": {"label": "Dîner", "items": [], "kcal": 0.0}
        }

        for p in products:
            p_data = self.get_product(p.get("product_id", ""))
            p_name = p_data.get("name", "Aliment") if p_data else "Aliment"
            amt = float(p.get("amount", 0.0) or 0.0)
            nutrients = p_data.get("nutrients", {}) if p_data else {}

            kcal = (nutrients.get("energy.energy", 0.0) or 0.0) * amt
            prot = (nutrients.get("nutrient.protein", 0.0) or 0.0) * amt
            carb = (nutrients.get("nutrient.carb", 0.0) or 0.0) * amt
            fat = (nutrients.get("nutrient.fat", 0.0) or 0.0) * amt

            day_kcal += kcal
            day_protein += prot
            day_carb += carb
            day_fat += fat

            daytime = p.get("daytime", "lunch")
            if daytime not in meals_dict:
                meals_dict[daytime] = {"label": daytime.capitalize(), "items": [], "kcal": 0.0}

            meals_dict[daytime]["items"].append(f"{p_name} ({round(amt)}g)")
            meals_dict[daytime]["kcal"] += kcal

        for sp in simple_products:
            s_name = sp.get("name", "Ajout rapide")
            nutrients = sp.get("nutrients", {})
            kcal = float(nutrients.get("energy.energy", 0.0) or 0.0)
            prot = float(nutrients.get("nutrient.protein", 0.0) or 0.0)
            carb = float(nutrients.get("nutrient.carb", 0.0) or 0.0)
            fat = float(nutrients.get("nutrient.fat", 0.0) or 0.0)

            day_kcal += kcal
            day_protein += prot
            day_carb += carb
            day_fat += fat

            daytime = sp.get("daytime", "lunch")
            if daytime not in meals_dict:
                meals_dict[daytime] = {"label": daytime.capitalize(), "items": [], "kcal": 0.0}

            meals_dict[daytime]["items"].append(f"{s_name}")
            meals_dict[daytime]["kcal"] += kcal

        for rp in recipe_portions:
            r_data = self.get_recipe(rp.get("recipe_id", ""))
            r_name = r_data.get("name", "Recette") if r_data else "Recette"
            portion_count = float(rp.get("portion_count", 1.0) or 1.0)
            recipe_total_portions = float(r_data.get("portion_count", 1.0) or 1.0) if r_data else 1.0
            nutrients = r_data.get("nutrients", {}) if r_data else {}

            kcal = ((nutrients.get("energy.energy", 0.0) or 0.0) / recipe_total_portions) * portion_count
            prot = ((nutrients.get("nutrient.protein", 0.0) or 0.0) / recipe_total_portions) * portion_count
            carb = ((nutrients.get("nutrient.carb", 0.0) or 0.0) / recipe_total_portions) * portion_count
            fat = ((nutrients.get("nutrient.fat", 0.0) or 0.0) / recipe_total_portions) * portion_count

            day_kcal += kcal
            day_protein += prot
            day_carb += carb
            day_fat += fat

            daytime = rp.get("daytime", "lunch")
            if daytime not in meals_dict:
                meals_dict[daytime] = {"label": daytime.capitalize(), "items": [], "kcal": 0.0}

            meals_dict[daytime]["items"].append(f"{r_name} ({portion_count} part(s))")
            meals_dict[daytime]["kcal"] += kcal

        # Fetch weight
        body_data = self.get_bodyvalues(date_str)
        w_list = body_data.get("weight", []) if body_data else []
        weight = w_list[-1]["value"] if w_list and "value" in w_list[-1] else None

        # Fetch exercises & steps
        ex_data = self.get_exercises(date_str)
        burned_kcal = 0.0
        steps = 0
        if ex_data:
            act = ex_data.get("activity", {}) or {}
            steps += int(act.get("steps", 0) or 0)
            burned_kcal += float(act.get("energy", 0.0) or 0.0)

            for tr in ex_data.get("training", []) or []:
                burned_kcal += float(tr.get("energy", 0.0) or 0.0)
                steps += int(tr.get("steps", 0) or 0)

            for ctr in ex_data.get("custom_training", []) or []:
                burned_kcal += float(ctr.get("energy", 0.0) or 0.0)

        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_names_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        day_fr = day_names_fr[dt.weekday()]

        return {
            "date": date_str,
            "day_name": day_fr,
            "day_short": dt.strftime("%d/%m"),
            "kcal": round(day_kcal),
            "protein": round(day_protein, 1),
            "carb": round(day_carb, 1),
            "fat": round(day_fat, 1),
            "weight": weight,
            "steps": steps,
            "burned_kcal": round(burned_kcal),
            "items_count": len(products) + len(simple_products) + len(recipe_portions),
            "meals": meals_dict
        }

    def get_weekly_summary(self, start_date: Optional[date] = None, end_date: Optional[date] = None, rolling_7d: bool = False) -> Dict[str, Any]:
        """Calculates and aggregates nutritional summary for the week or date range."""
        today = date.today()
        if rolling_7d:
            start_date = today - timedelta(days=6)
            end_date = today
        else:
            if not start_date:
                start_date = today - timedelta(days=today.weekday())  # Monday
            if not end_date:
                end_date = today

        days = []
        total_kcal = 0.0
        total_protein = 0.0
        total_carb = 0.0
        total_fat = 0.0
        active_days = 0

        curr = start_date
        while curr <= end_date:
            curr_str = curr.strftime("%Y-%m-%d")
            daily = self.get_daily_summary(curr_str)
            days.append(daily)

            if daily["kcal"] > 0 or daily["items_count"] > 0:
                active_days += 1
                total_kcal += daily["kcal"]
                total_protein += daily["protein"]
                total_carb += daily["carb"]
                total_fat += daily["fat"]

            curr += timedelta(days=1)

        # Weight calculation
        weights = [d["weight"] for d in days if d.get("weight") is not None]
        avg_weight = round(sum(weights) / len(weights), 1) if weights else None
        latest_weight = weights[-1] if weights else None

        # Activity calculation (filter meaningful active days)
        step_days = [d for d in days if d.get("steps", 0) > 500]
        avg_steps = round(sum(d["steps"] for d in step_days) / len(step_days)) if step_days else 0

        burned_days = [d for d in days if d.get("burned_kcal", 0) > 50]
        avg_burned = round(sum(d["burned_kcal"] for d in burned_days) / len(burned_days)) if burned_days else 0

        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "start_short": start_date.strftime("%d/%m"),
            "end_short": end_date.strftime("%d/%m"),
            "days": days,
            "total_kcal": round(total_kcal),
            "total_protein": round(total_protein, 1),
            "total_carb": round(total_carb, 1),
            "total_fat": round(total_fat, 1),
            "active_days": active_days,
            "avg_kcal": round(total_kcal / active_days) if active_days > 0 else 0,
            "avg_protein": round(total_protein / active_days, 1) if active_days > 0 else 0.0,
            "avg_carb": round(total_carb / active_days, 1) if active_days > 0 else 0.0,
            "avg_fat": round(total_fat / active_days, 1) if active_days > 0 else 0.0,
            "avg_weight": avg_weight,
            "latest_weight": latest_weight,
            "avg_steps": avg_steps,
            "avg_burned_kcal": avg_burned
        }

    def format_weekly_summary(self, summary: Dict[str, Any]) -> str:
        """Formats the weekly summary into a readable Telegram markdown message."""
        formatted_steps = f"{summary.get('avg_steps', 0):,}".replace(",", " ")
        lines = [
            f"📊 *Bilan de la semaine ({summary['start_short']} au {summary['end_short']})*",
            "",
            "📈 *Moyennes journalières :*",
            f"🔥 Consommation : *{summary['avg_kcal']} kcal* / jour",
            f"🏃 Calories brûlées : *{summary.get('avg_burned_kcal', 0)} kcal* / jour",
            f"👟 Pas : *{formatted_steps}* pas / jour"
        ]

        if summary.get("avg_weight") is not None:
            w_str = f"⚖️ Poids moyen : *{summary['avg_weight']} kg*"
            if summary.get("latest_weight") and summary["latest_weight"] != summary["avg_weight"]:
                w_str += f" _(actuel : {summary['latest_weight']} kg)_"
            lines.append(w_str)

        lines.extend([
            f"🥩 Protéines : *{summary['avg_protein']}g* | 🍞 Glucides : *{summary['avg_carb']}g* | 🥑 Lipides : *{summary['avg_fat']}g*",
            "",
            "🗓 *Détail par jour :*"
        ])

        for day in summary["days"]:
            meta_parts = []
            if day.get("weight"):
                meta_parts.append(f"⚖️ {day['weight']} kg")
            if day.get("steps"):
                meta_parts.append(f"👟 {day['steps']} pas")
            if day.get("burned_kcal"):
                meta_parts.append(f"🔥 -{day['burned_kcal']} kcal")

            meta_str = f" | {' • '.join(meta_parts)}" if meta_parts else ""
            lines.append(f"\n🔹 *{day['day_name']} {day['day_short']}* — *{day['kcal']} kcal* (P: {day['protein']}g | G: {day['carb']}g | L: {day['fat']}g){meta_str}")

            has_items = False
            for _, mdata in day["meals"].items():
                if mdata["items"]:
                    has_items = True
                    items_str = ", ".join(mdata["items"])
                    lines.append(f"  ▫️ *{mdata['label']}* ({round(mdata['kcal'])} kcal) : {items_str}")
            if not has_items:
                lines.append("  ▫️ _Aucune saisie alimentaire_")

        return "\n".join(lines)

    def format_daily_summary(self, daily: Dict[str, Any]) -> str:
        """Formats a single day summary into a readable Telegram markdown message."""
        lines = [
            f"📊 *Bilan du {daily['day_name']} {daily['day_short']}*",
            "",
            f"🔥 *Consommation : {daily['kcal']} kcal* (P: {daily['protein']}g | G: {daily['carb']}g | L: {daily['fat']}g)"
        ]

        if daily.get("burned_kcal") or daily.get("steps"):
            lines.append(f"🏃 *Activité :* {daily.get('burned_kcal', 0)} kcal brûlées • 👟 {daily.get('steps', 0)} pas")

        if daily.get("weight"):
            lines.append(f"⚖️ *Poids :* {daily['weight']} kg")

        lines.extend([
            "",
            "🍽 *Détail des repas :*"
        ])

        has_items = False
        for _, mdata in daily["meals"].items():
            if mdata["items"]:
                has_items = True
                items_str = ", ".join(mdata["items"])
                lines.append(f"  ▫️ *{mdata['label']}* ({round(mdata['kcal'])} kcal) : {items_str}")
        if not has_items:
            lines.append("  ▫️ _Aucune saisie alimentaire_")

        return "\n".join(lines)
