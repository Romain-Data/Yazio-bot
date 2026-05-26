import os
from google import genai
from pydantic import BaseModel, Field
from typing import List

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

class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be set in the environment.")
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.5-flash-lite"

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
        Réponds UNIQUEMENT au format JSON en respectant le schéma demandé.
        """
        
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RepasAnalysis
            )
        )
        
        return RepasAnalysis.model_validate_json(response.text)
        
    def analyze_image(self, image_data: bytes, mime_type: str, text: str = "", local_time: str = None) -> RepasAnalysis:
        """
        Analyzes an image of a meal, optionally assisted by user text.
        Extracts food items from the visual content and estimates their nutritional values.
        """
        prompt = f"""
        Tu es un expert en nutrition. L'utilisateur a pris une photo de son repas.
        {f'Il a ajouté le commentaire suivant : "{text}"' if text else ''}
        
        L'heure locale est : {local_time or 'inconnue'}.
        
        Identifie les aliments sur la photo, estime leurs portions (en grammes) et leurs valeurs nutritionnelles.
        Déduis le type de repas (breakfast, lunch, snack, dinner) en fonction de l'heure ou des aliments.
        ATTENTION : Si l'utilisateur précise explicitement le type de repas dans son message (ex: "petit déjeuner", "déjeuner", "dîner", "snack", "goûter"), tu DOIS utiliser cette information en priorité absolue.
        ATTENTION RECETTE : Si l'utilisateur précise "(recette)" à côté d'un aliment, passe la valeur `is_recipe` à `true` pour cet aliment, et retire la mention "(recette)" de son nom. Sinon laisse à `false`.
        Réponds UNIQUEMENT au format JSON en respectant le schéma demandé.
        """
        
        image_part = genai.types.Part.from_bytes(
            data=image_data,
            mime_type=mime_type,
        )
        
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=[prompt, image_part],
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RepasAnalysis
            )
        )
        
        return RepasAnalysis.model_validate_json(response.text)

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
        Réponds UNIQUEMENT au format JSON en respectant le schéma demandé.
        """
        
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RepasAnalysis
            )
        )
        
        return RepasAnalysis.model_validate_json(response.text)
