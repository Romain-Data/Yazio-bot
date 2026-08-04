import base64
import os
import json
import requests
from pydantic import BaseModel, Field
from typing import List


# Note: The field descriptions are deliberately in French
# to optimize the performance of AI comprehension and generation.
class Aliment(BaseModel):
    nom: str = Field(description="Nom usuel de l'aliment")
    quantite_g: float = Field(description="Quantité estimée en grammes")
    kcal: float = Field(description="Calories estimées pour cette quantité")
    proteines: float = Field(description="Protéines en grammes pour cette quantité")
    glucides: float = Field(description="Glucides en grammes pour cette quantité")
    lipides: float = Field(description="Lipides en grammes pour cette quantité")
    is_recipe: bool = Field(default=False, description="True si l'utilisateur a précisé '(recette)' à côté de cet aliment")
    yazio_name: str | None = Field(default=None, description="Nom officiel trouvé dans Yazio")


class RepasAnalysis(BaseModel):
    repas: str = Field(description="Type de repas: 'breakfast', 'lunch', 'dinner' ou 'snack'")
    aliments: List[Aliment] = Field(description="Liste des aliments identifiés")
    total_kcal: float = Field(description="Total des calories")
    total_proteines: float = Field(description="Total des protéines")
    total_glucides: float = Field(description="Total des glucides")
    total_lipides: float = Field(description="Total des lipides")
    is_creation_recette: bool = Field(default=False, description="True si l'utilisateur demande explicitement de créer une NOUVELLE recette")
    nom_recette: str | None = Field(default=None, description="Nom de la nouvelle recette à créer (ex: 'Gâteau au chocolat')")
    portions: int = Field(default=1, description="Nombre de portions de la recette si précisé (sinon 1)")
    is_creation_equivalence: bool = Field(default=False, description="True si l'utilisateur demande d'ajouter une équivalence de poids (ex: 'Nouvelle équivalence : 1 tranche de jambon 40g')")
    equivalence_key: str | None = Field(default=None, description="L'aliment et l'unité pour l'équivalence (ex: '1 tranche de jambon')")
    equivalence_value: str | None = Field(default=None, description="Le poids en grammes pour l'équivalence (ex: '40g')")
    is_estimation: bool = Field(default=False, description="True si l'utilisateur demande une estimation (si le texte contient le mot 'estimation', 'estime' ou 'estimer') ou si le repas est décrit de manière globale/floue.")
    nom_estimation: str | None = Field(default=None, description="Nom descriptif global du repas estimé (ex: 'Pâtes carbonara au restaurant')")
    questions: List[str] = Field(default=[], description="Jusqu'à 3 questions courtes pour affiner l'estimation globale si nécessaire")
    is_activity: bool = Field(default=False, description="True si l'utilisateur décrit une activité physique ou un entraînement (ex: '1h30 de tennis', '3h de piscine', '30 min de course') plutôt qu'un repas.")
    nom_activite: str | None = Field(default=None, description="Nom descriptif de l'activité physique (ex: 'Entraînement de tennis', 'Jeu dans une piscine')")
    duree_minutes: int | None = Field(default=None, description="Durée de l'activité en minutes (ex: 90, 180, 30)")
    calories_brules: float | None = Field(default=None, description="Estimation des calories brûlées (kcal) par cette activité en fonction du type d'activité, de la durée, et de l'intensité.")


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
            "response_format": {"type": "json_object"},
            "max_tokens": 4096
        }

        max_retries = 3
        last_exception = None

        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()

                result_data = response.json()
                content = result_data["choices"][0]["message"]["content"]
                return RepasAnalysis.model_validate_json(content)
            except Exception as e:
                last_exception = e  # Keep track of the last error to raise if all retries fail
                print(f"Attempt {attempt + 1}/{max_retries} failed with error: {e}")

        raise last_exception

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
        ESTIMATION GLOBALE (AJOUT RAPIDE) (PRIORITÉ ABSOLUE) : Si le texte de l'utilisateur contient le mot "estimation" (ex: "Snack. Estimation"), "estime" ou "estimer", tu DOIS impérativement passer `is_estimation` à `true`. C'est une demande explicite d'estimation globale. De même, si l'utilisateur décrit un repas de manière globale/floue sans pouvoir lister les ingrédients précisément (ex: "un plat de pâtes au restaurant", "un burger frites chez le boucher", "un couscous chez des amis"), passe `is_estimation` à `true`. Dans tous ces cas :
        - Extrais un nom descriptif global pour le repas dans `nom_estimation` (ex: "Tarte tatin maison et café au lait").
        - Estime les calories et macronutriments pour l'ensemble du repas et place-les dans `total_kcal`, `total_proteines`, `total_glucides` et `total_lipides`.
        - Dans la liste `aliments`, place un unique aliment représentant cette estimation globale (ex: nom = valeur de `nom_estimation`, quantité = 1g, calories et macros = totaux du repas).
        - Rédige dans la liste `questions` jusqu'à 3 questions ciblées et courtes en français pour aider à affiner l'estimation si elle est floue (ex: présence de sauce/huile, portion petite/normale/grande, ingrédients clés, type de viande/cuisson). Laisse la liste `questions` vide si l'estimation est déjà très précise ou si ce n'est pas une estimation.
        
        ACTIVITÉ PHYSIQUE (PRIORITÉ ABSOLUE SUR L'ALIMENTATION) : Si le texte décrit une activité physique, un sport ou un entraînement (ex: "3h de jeu dans une piscine avec mes enfants", "1h30 d'entrainement de tennis", "30 minutes de footing"), tu DOIS impérativement :
        - Passer `is_activity` à `true`.
        - Extraire le nom descriptif de l'activité dans `nom_activite` (ex: "Jeu piscine avec enfants", "Entraînement de tennis", "Footing").
        - Extraire ou estimer la durée de l'activité en minutes dans `duree_minutes` (ex: 180, 90, 30).
        - Estimer la dépense calorique dans `calories_brules` de manière TRÈS PRUDENTE et réaliste (pour un adulte de 75 kg) en respectant les repères suivants :
          * Activité faible / de loisir (ex: jouer dans l'eau avec des enfants, marche tranquille, rangement/jardinage) : environ 2,5 à 3 kcal/min (soit ~150-180 kcal/heure). Par exemple, pour 3h de jeu en piscine, cela représente environ 400 à 450 kcal maximum (en comptant les pauses).
          * Activité modérée (ex: tennis de table, vélo tranquille, jeux de ballons actifs) : environ 5 à 6 kcal/min (soit ~300-360 kcal/heure).
          * Activité intense / sport soutenu (ex: tennis match, footing, natation active continue) : environ 8 à 10 kcal/min (soit ~480-600 kcal/heure).
        - Si la description contient des termes flous quant à l'intensité ou les conditions (ex: "piscine avec les enfants", "vélo en famille"), tu DOIS impérativement poser jusqu'à 3 questions courtes et polies dans la liste `questions` pour affiner (ex: "S'agissait-il de natation continue ou plutôt de jeux calmes dans l'eau ?", "Y a-t-il eu des temps de repos durant ces 3 heures ?") ET retenir l'estimation basse par défaut.
        - Laisser la liste `aliments` vide.
        - Positionner `repas` à "snack" et mettre les totaux nutritionnels (`total_kcal`, `total_proteines`, `total_glucides`, `total_lipides`) à 0.


        
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
        ESTIMATION GLOBALE (AJOUT RAPIDE) (PRIORITÉ ABSOLUE) : Si le texte de l'utilisateur contient le mot "estimation" (ex: "Snack. Estimation"), "estime" ou "estimer", tu DOIS impérativement passer `is_estimation` à `true`. C'est une demande explicite d'estimation globale. De même, si l'utilisateur décrit un repas de manière globale/floue sans pouvoir lister les ingrédients précisément (ex: "un plat de pâtes au restaurant", "un burger frites chez le boucher", "un couscous chez des amis"), passe `is_estimation` à `true`. Dans tous ces cas :
        - Extrais un nom descriptif global pour le repas dans `nom_estimation` (ex: "Tarte tatin maison et café au lait").
        - Estime les calories et macronutriments pour l'ensemble du repas et place-les dans `total_kcal`, `total_proteines`, `total_glucides` et `total_lipides`.
        - Dans la liste `aliments`, place un unique aliment représentant cette estimation globale (ex: nom = valeur de `nom_estimation`, quantité = 1g, calories et macros = totaux du repas).
        - Rédige dans la liste `questions` jusqu'à 3 questions ciblées et courtes en français pour aider à affiner l'estimation si elle est floue (ex: présence de sauce/huile, portion petite/normale/grande, ingrédients clés, type de viande/cuisson). Laisse la liste `questions` vide si l'estimation est déjà très précise ou si ce n'est pas une estimation.


        
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
        ESTIMATION GLOBALE (AJOUT RAPIDE) : Si la correction indique qu'il s'agit d'une estimation globale (ou si l'analyse originale était une estimation et qu'on la corrige), conserve ou passe `is_estimation` à `true`, et ajuste `nom_estimation` et les valeurs nutritionnelles associées. Dans ce cas, la liste `aliments` doit contenir un unique aliment représentant cette estimation globale.
        - De plus, si l'utilisateur a répondu aux questions d'affinage précédentes dans son message de correction, prends en compte ses réponses pour affiner les calories et macros, puis retire ces questions résolues de la liste `questions`. S'il reste des incertitudes majeures, tu peux formuler de nouvelles questions d'affinage (maximum 3 au total). Si l'estimation est désormais assez précise, laisse la liste `questions` vide.
        
        ACTIVITÉ PHYSIQUE : Si la correction concerne une activité physique, ou si l'analyse originale concernait une activité physique et qu'on la corrige, conserve `is_activity` à `true`. Ajuste `nom_activite`, `duree_minutes` et `calories_brules` en fonction des réponses ou corrections de l'utilisateur, en restant très réaliste et prudent (ex: 2.5-3 kcal/min pour loisir/jeux piscine, 5-6 kcal/min pour modéré, 8-10 kcal/min pour intense). Si l'utilisateur a répondu aux questions d'affinage précédentes pour l'activité (comme confirmer le niveau d'intensité ou les temps de pause), prends en compte ses réponses pour ajuster la dépense calorique de manière précise, puis retire ces questions résolues de la liste `questions`. S'il reste des incertitudes majeures, tu peux formuler de nouvelles questions d'affinage (maximum 3 au total). Si l'estimation est désormais assez précise, laisse la liste `questions` vide.

        
        EQUIVALENCES DE POIDS PERSONNALISÉES (TRÈS IMPORTANT) :
        Voici une table de correspondance de poids que tu DOIS ABSOLUMENT utiliser pour tes conversions si l'aliment correspond sémantiquement.
        Cependant, si l'utilisateur précise un poids exact en grammes dans sa correction (ex: "jambon 60g"), ce poids exact a toujours la priorité absolue sur la table.
        {self._load_custom_weights()}
        
        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {RepasAnalysis.model_json_schema()}
        """
        return self._call_api(prompt)
