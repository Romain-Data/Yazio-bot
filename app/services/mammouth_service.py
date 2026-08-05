import base64
import os
import json
import re
from app.models.analysis import RepasAnalysis
from app.services.extractors.meal_extractor import MealExtractor
from app.services.extractors.activity_extractor import ActivityExtractor
from app.services.extractors.recipe_extractor import RecipeExtractor
from app.services.extractors.equivalence_extractor import EquivalenceExtractor
from app.services.extractors.estimation_extractor import EstimationExtractor


class MammouthService:
    def __init__(self):
        self.api_key = os.getenv("MAMMOUTH_API_KEY")
        if not self.api_key:
            raise ValueError("MAMMOUTH_API_KEY must be set in the environment.")
        self.api_url = "https://api.mammouth.ai/v1/chat/completions"
        self.model_id = os.getenv("MAMMOUTH_MODEL_ID", "gemini-2.5-flash-lite")
        self.custom_weights_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "custom_weights.json"
        )

        # Instantiate modular extractors
        self.meal_extractor = MealExtractor(self.api_key, self.api_url, self.model_id)
        self.activity_extractor = ActivityExtractor(self.api_key, self.api_url, self.model_id)
        self.recipe_extractor = RecipeExtractor(self.api_key, self.api_url, self.model_id)
        self.equivalence_extractor = EquivalenceExtractor(self.api_key, self.api_url, self.model_id)
        self.estimation_extractor = EstimationExtractor(self.api_key, self.api_url, self.model_id)

    def _load_custom_weights(self) -> str:
        if os.path.exists(self.custom_weights_file):
            try:
                with open(self.custom_weights_file, "r") as f:
                    data = json.load(f)
                    if data:
                        return json.dumps(data, ensure_ascii=False)
            except Exception:
                pass
        return "{}"

    def save_custom_weight(self, eq_key: str, eq_val: str) -> None:
        """Saves a custom weight equivalence to the JSON file."""
        data = {}
        if os.path.exists(self.custom_weights_file):
            try:
                with open(self.custom_weights_file, "r") as f:
                    data = json.load(f)
            except Exception:
                pass

        data[eq_key] = eq_val

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.custom_weights_file), exist_ok=True)
        with open(self.custom_weights_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _detect_intent(self, text: str) -> str:
        if not text:
            return "meal"

        # Clean leading punctuation/whitespace/emojis (keep alphanumeric at the beginning)
        cleaned = re.sub(
            r'^[^a-zA-Z0-9àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ]*', '', text
        ).strip().lower()

        # 1. Explicit Prefix Matches (Highest Priority)
        if re.match(
            r'^(activité|activite|sport|seance|séance|footing|course|tennis|velo|vélo|muscu|piscine)\b',
            cleaned,
        ):
            return "activity"
        if re.match(
            r'^(recette|nouvelle recette|creer recette|créer recette)\b', cleaned
        ):
            return "recipe"
        if re.match(
            r'^(equivalence|équivalence|nouvelle equivalence|nouvelle équivalence)\b',
            cleaned,
        ):
            return "equivalence"
        if re.match(r'^(estimation|estime|estimer|estim)\b', cleaned):
            return "estimation"

        # 2. Implicit Activity Matches (No explicit prefix, but activity keywords and no meal indicators)
        activity_keywords = [
            "sport", "entrainement", "entraînement", "footing", "tennis",
            "velo", "vélo", "muscu", "piscine", "course", "jogging",
            "marche", "gym", "cardio", "fitness", "randonnée", "rando",
            "natation", "pédaler", "pedaler", "courir", "nager"
        ]
        meal_indicators = [
            "repas", "mangé", "manger", "mange", "bu", "boire", "déjeuner",
            "dîner", "diner", "goûter", "gouter", "collation", "snack",
            "petit-déjeuner", "petit déjeuner", "petit dej"
        ]

        has_activity = any(kw in cleaned for kw in activity_keywords)
        has_meal = any(ind in cleaned for ind in meal_indicators)

        if has_activity and not has_meal:
            return "activity"

        return "meal"

    def analyze_text(self, text: str, local_time: str = None) -> RepasAnalysis:
        """
        Analyzes a textual description of a meal or activity.
        Routes to the appropriate specialized extractor.
        """
        intent = self._detect_intent(text)
        custom_weights = self._load_custom_weights()

        if intent == "activity":
            return self.activity_extractor.analyze_text(text, local_time)
        elif intent == "recipe":
            return self.recipe_extractor.analyze_text(text, local_time)
        elif intent == "equivalence":
            return self.equivalence_extractor.analyze_text(text, local_time)
        elif intent == "estimation":
            return self.estimation_extractor.analyze_text(text, local_time)
        else:
            return self.meal_extractor.analyze_text(text, local_time, custom_weights)

    def analyze_image(
        self,
        image_data: bytes,
        mime_type: str,
        text: str = "",
        local_time: str = None,
    ) -> RepasAnalysis:
        """
        Analyzes an image of a meal, optionally assisted by user text.
        """
        intent = self._detect_intent(text)
        custom_weights = self._load_custom_weights()

        base64_image = base64.b64encode(image_data).decode("utf-8")
        image_part = {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
        }

        if intent == "activity":
            return self.activity_extractor.analyze_text(text, local_time)
        elif intent == "recipe":
            return self.recipe_extractor.analyze_text(text, local_time)
        elif intent == "equivalence":
            return self.equivalence_extractor.analyze_text(text, local_time)
        elif intent == "estimation":
            return self.estimation_extractor.analyze_image(image_part, text, local_time)
        else:
            return self.meal_extractor.analyze_image(
                image_part, text, local_time, custom_weights
            )

    def analyze_correction(
        self,
        original_analysis: RepasAnalysis,
        correction: str,
        local_time: str = None,
    ) -> RepasAnalysis:
        """
        Applies a natural language correction to a previous analysis.
        """
        custom_weights = self._load_custom_weights()

        if getattr(original_analysis, "is_activity", False):
            return self.activity_extractor.analyze_correction(
                original_analysis, correction, local_time
            )
        elif getattr(original_analysis, "is_creation_recette", False):
            return self.recipe_extractor.analyze_correction(
                original_analysis, correction, local_time
            )
        elif getattr(original_analysis, "is_creation_equivalence", False):
            return self.equivalence_extractor.analyze_correction(
                original_analysis, correction, local_time
            )
        elif getattr(original_analysis, "is_estimation", False):
            return self.estimation_extractor.analyze_correction(
                original_analysis, correction, local_time
            )
        else:
            return self.meal_extractor.analyze_correction(
                original_analysis, correction, local_time, custom_weights
            )
