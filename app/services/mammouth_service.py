import base64
import os
import json
import requests
import requests
from pydantic import BaseModel, Field
from typing import List, Optional


class Aliment(BaseModel):
    nom: str = Field(description="Nom usuel de l'aliment")
    quantite_g: float = Field(description="Quantité estimée en grammes")
    kcal: float = Field(description="Calories estimées pour cette quantité")
    proteines: float = Field(description="Protéines en grammes pour cette quantité")
    glucides: float = Field(description="Glucides en grammes pour cette quantité")
    lipides: float = Field(description="Lipides en grammes pour cette quantité")
    is_recipe: bool = Field(default=False, description="True si l'utilisateur a précisé '(recette)' à côté de cet aliment")


class RepasAnalysis(BaseModel):
    repas: str = Field(description="Type de repas: 'breakfast', 'lunch', 'dinner' ou 'snack'")
    aliments: List[Aliment] = Field(description="Liste des aliments identifiés")
    total_kcal: float = Field(description="Total des calories")
    total_proteines: float = Field(description="Total des protéines")
    total_glucides: float = Field(description="Total des glucides")
    total_lipides: float = Field(description="Total des lipides")
    is_creation_recette: bool = Field(default=False, description="True si l'utilisateur demande explicitement de créer une NOUVELLE recette")
    nom_recette: Optional[str] = Field(default=None, description="Nom de la nouvelle recette à créer (ex: 'Gâteau au chocolat')")
    portions: int = Field(default=1, description="Nombre de portions de la recette si précisé (sinon 1)")
    is_creation_equivalence: bool = Field(default=False, description="True si l'utilisateur demande d'ajouter une équivalence de poids (ex: 'Nouvelle équivalence : 1 tranche de jambon 40g')")
    equivalence_key: Optional[str] = Field(default=None, description="L'aliment et l'unité pour l'équivalence (ex: '1 tranche de jambon')")
    equivalence_value: Optional[str] = Field(default=None, description="Le poids en grammes pour l'équivalence (ex: '40g')")


class MammouthService:
    def __init__(self):
        self.api_key = os.getenv("MAMMOUTH_API_KEY")
        if not self.api_key:
            raise ValueError("MAMMOUTH_API_KEY must be set in the environment.")
        self.api_url = "https://api.mammouth.ai/v1/chat/completions"
        self.model_id = os.getenv("MAMMOUTH_MODEL_ID", "gemini-2.5-flash-lite")
        self.custom_weights_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "custom_weights.json")

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

    def _call_api(self, prompt: str, image_part: dict = None) -> RepasAnalysis:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        content_list = [{"type": "text", "text": prompt}]
        if image_part:
            content_list.append(image_part)

        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": content_list
                }
            ],
            "response_format": {"type": "json_object"}
        }

        response = requests.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()

        result_data = response.json()
        content = result_data["choices"][0]["message"]["content"]
        return RepasAnalysis.model_validate_json(content)

    def analyze_text(self, text: str, local_time: str = None) -> RepasAnalysis:
        """
        Analyzes a textual description of a meal.
        Extracts food items, estimates nutritional values, and infers meal type.
        """
        prompt = f"""
        Tu es un expert en nutrition. L'utilisateur vient de manger le repas suivant :
        "{text}"
        
        L'heure locale est : {local_time or 'inconnue'}.
        
        Estime les valeurs nutritionnelles de chaque aliment décrit.
        Déduis le type de repas (breakfast, lunch, snack, dinner) en fonction de l'heure ou de la description.
        ATTENTION : Si l'utilisateur précise explicitement le type de repas dans son message (ex: "petit déjeuner", "déjeuner", "dîner", "snack", "goûter"), tu DOIS utiliser cette information en priorité absolue.
        ATTENTION RECETTE : Si l'utilisateur précise "(recette)" à côté d'un aliment, passe la valeur `is_recipe` à `true` pour cet aliment, et retire la mention "(recette)" de son nom. Sinon laisse à `false`.
        CREATION DE RECETTE : Si le message indique qu'il faut créer une recette (ex: "Nouvelle recette : Gâteau au chocolat", "Créer recette"), passe `is_creation_recette` à `true`, extrait le nom dans `nom_recette` et le nombre de portions dans `portions`. Les aliments seront alors les ingrédients de la recette.
        CREATION EQUIVALENCE : Si le message indique qu'il faut créer une nouvelle équivalence de poids (ex: "Nouvelle équivalence : 1 tranche de jambon 40g"), passe `is_creation_equivalence` à `true`, extrait l'aliment dans `equivalence_key` et le poids dans `equivalence_value`.
        
        EQUIVALENCES DE POIDS PERSONNALISÉES (TRÈS IMPORTANT) :
        Voici une table de correspondance de poids que tu DOIS ABSOLUMENT utiliser pour tes conversions si l'aliment correspond sémantiquement.
        Cependant, si l'utilisateur précise un poids exact en grammes dans son message (ex: "jambon 60g"), ce poids exact a toujours la priorité absolue sur la table.
        {self._load_custom_weights()}
        
        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {RepasAnalysis.model_json_schema()}
        """
        return self._call_api(prompt)

    def analyze_image(self, image_data: bytes, mime_type: str, text: str = "", local_time: str = None) -> RepasAnalysis:
        """
        Analyzes an image of a meal, optionally assisted by user text.
        Extracts food items from the visual content and estimates their nutritional values.
        """
        base64_image = base64.b64encode(image_data).decode("utf-8")
        image_part = {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_image}"
            }
        }

        prompt = f"""
        Tu es un expert en nutrition. L'utilisateur a pris une photo de son repas.
        {f'Il a ajouté le commentaire suivant : "{text}"' if text else ''}
        
        L'heure locale est : {local_time or 'inconnue'}.
        
        Identifie les aliments sur la photo, estime leurs portions (en grammes) et leurs valeurs nutritionnelles.
        Déduis le type de repas (breakfast, lunch, snack, dinner) en fonction de l'heure ou des aliments.
        ATTENTION : Si l'utilisateur précise explicitement le type de repas dans son message (ex: "petit déjeuner", "déjeuner", "dîner", "snack", "goûter"), tu DOIS utiliser cette information en priorité absolue.
        ATTENTION RECETTE : Si l'utilisateur précise "(recette)" à côté d'un aliment, passe la valeur `is_recipe` à `true` pour cet aliment, et retire la mention "(recette)" de son nom. Sinon laisse à `false`.
        CREATION DE RECETTE : Si le message indique qu'il faut créer une recette (ex: "Nouvelle recette : Gâteau au chocolat", "Créer recette"), passe `is_creation_recette` à `true`, extrait le nom dans `nom_recette` et le nombre de portions dans `portions`. Les aliments seront alors les ingrédients de la recette.
        CREATION EQUIVALENCE : Si le message indique qu'il faut créer une nouvelle équivalence de poids, passe `is_creation_equivalence` à `true`, extrait l'aliment dans `equivalence_key` et le poids dans `equivalence_value`.
        
        EQUIVALENCES DE POIDS PERSONNALISÉES (TRÈS IMPORTANT) :
        Voici une table de correspondance de poids que tu DOIS ABSOLUMENT utiliser pour tes conversions si l'aliment correspond sémantiquement.
        Cependant, si l'utilisateur précise un poids exact en grammes dans son message (ex: "jambon 60g"), ce poids exact a toujours la priorité absolue sur la table.
        {self._load_custom_weights()}
        
        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {RepasAnalysis.model_json_schema()}
        """
        return self._call_api(prompt, image_part)

    def analyze_correction(self, original_analysis: RepasAnalysis, correction: str, local_time: str = None) -> RepasAnalysis:
        """
        Corrects an existing nutritional analysis based on user feedback.
        Adjusts quantities, adds or removes items, or changes the meal type as requested.
        """
        prompt = f"""
        Tu es un expert en nutrition. Voici l'analyse nutritionnelle que tu avais précédemment estimée :
        {original_analysis.model_dump_json()}
        
        L'utilisateur demande la correction suivante :
        "{correction}"
        
        L'heure locale est : {local_time or 'inconnue'}.
        
        Modifie l'analyse originale en prenant en compte la correction de l'utilisateur (ajoute, supprime ou modifie les quantités des aliments).
        Conserve ou adapte le type de repas (breakfast, lunch, snack, dinner). 
        ATTENTION : Si l'utilisateur précise explicitement le type de repas dans sa correction (ex: "C'est un petit déjeuner", "dîner", etc.), tu DOIS mettre à jour le type de repas.
        ATTENTION RECETTE : Si l'utilisateur précise "(recette)" à côté d'un aliment corrigé ou ajouté, passe la valeur `is_recipe` à `true` pour cet aliment, et retire la mention "(recette)" de son nom.
        CREATION DE RECETTE : Si la correction indique qu'il s'agit finalement d'une création de recette, passe `is_creation_recette` à `true` et ajuste `nom_recette` et `portions`.
        CREATION EQUIVALENCE : Si le message indique qu'il faut créer une nouvelle équivalence de poids, passe `is_creation_equivalence` à `true`.
        
        EQUIVALENCES DE POIDS PERSONNALISÉES (TRÈS IMPORTANT) :
        Voici une table de correspondance de poids que tu DOIS ABSOLUMENT utiliser pour tes conversions si l'aliment correspond sémantiquement.
        Cependant, si l'utilisateur précise un poids exact en grammes dans sa correction (ex: "jambon 60g"), ce poids exact a toujours la priorité absolue sur la table.
        {self._load_custom_weights()}
        
        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {RepasAnalysis.model_json_schema()}
        """
        return self._call_api(prompt)
