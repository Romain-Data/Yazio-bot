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
    yazio_name: Optional[str] = Field(default=None, description="Nom officiel trouvé dans Yazio")


class BaseMealAnalysis(BaseModel):
    repas: str = Field(description="Type de repas: 'breakfast', 'lunch', 'dinner' ou 'snack'")
    aliments: List[Aliment] = Field(description="Liste des aliments identifiés")
    total_kcal: float = Field(description="Total des calories")
    total_proteines: float = Field(description="Total des protéines")
    total_glucides: float = Field(description="Total des glucides")
    total_lipides: float = Field(description="Total des lipides")


class RecipeFields(BaseModel):
    is_creation_recette: bool = Field(default=False, description="True si l'utilisateur demande de créer une recette")
    nom_recette: Optional[str] = Field(default=None, description="Nom de la nouvelle recette à créer")
    portions: int = Field(default=1, description="Nombre de portions de la recette")


class EquivalenceFields(BaseModel):
    is_creation_equivalence: bool = Field(default=False, description="True si l'utilisateur demande d'ajouter une équivalence")
    equivalence_key: Optional[str] = Field(default=None, description="L'aliment et l'unité pour l'équivalence")
    equivalence_value: Optional[str] = Field(default=None, description="Le poids en grammes pour l'équivalence")


class EstimationFields(BaseModel):
    is_estimation: bool = Field(default=False, description="True si estimation globale demandée ou repas flou")
    nom_estimation: Optional[str] = Field(default=None, description="Nom descriptif global du repas estimé")
    questions: List[str] = Field(default=[], description="Questions courtes pour affiner l'estimation")


class ActivityFields(BaseModel):
    is_activity: bool = Field(default=False, description="True si l'utilisateur décrit une activité physique")
    nom_activite: Optional[str] = Field(default=None, description="Nom descriptif de l'activité physique")
    duree_minutes: Optional[int] = Field(default=None, description="Durée de l'activité en minutes")
    calories_brules: Optional[float] = Field(default=None, description="Estimation des calories brûlées (kcal)")


class RepasAnalysis(BaseMealAnalysis, RecipeFields, EquivalenceFields, EstimationFields, ActivityFields):
    is_prompt: bool = Field(default=False, description="True s'il s'agit d'une question interactive sans données extraites")


class IntentAnalysis(BaseModel):
    intent: str = Field(description="L'intention détectée : 'activity', 'recipe_creation', 'equivalence_creation', 'global_estimation', 'meal_logging'")


class ActivityOnlyAnalysis(BaseModel):
    nom_activite: str = Field(description="Nom descriptif de l'activité physique (ex: 'Entraînement de tennis')")
    duree_minutes: int = Field(description="Durée de l'effort physique actif réel en minutes (ex: 90, 180)")
    calories_brules: float = Field(description="Estimation réaliste et prudente des calories brûlées (kcal)")
    questions: List[str] = Field(default=[], description="Jusqu'à 3 questions courtes d'affinage si l'intensité/conditions sont floues")


class RecipeCreationOnlyAnalysis(BaseModel):
    nom_recette: str = Field(description="Nom de la nouvelle recette à créer (ex: 'Gâteau au chocolat')")
    portions: int = Field(default=1, description="Nombre de portions de la recette")
    ingredients: List[Aliment] = Field(description="Les ingrédients composant la recette")


class EquivalenceOnlyAnalysis(BaseModel):
    equivalence_key: str = Field(description="L'aliment et l'unité pour l'équivalence (ex: '1 tranche de jambon')")
    equivalence_value: str = Field(description="Le poids associé en grammes (ex: '40g')")


class GlobalEstimationOnlyAnalysis(BaseModel):
    repas: str = Field(description="Type de repas: 'breakfast', 'lunch', 'dinner' ou 'snack'")
    nom_estimation: str = Field(description="Nom descriptif global pour le repas (ex: 'Tarte tatin maison et café au lait')")
    total_kcal: float = Field(description="Total des calories pour l'ensemble du repas")
    total_proteines: float = Field(description="Total des protéines")
    total_glucides: float = Field(description="Total des glucides")
    total_lipides: float = Field(description="Total des lipides")
    questions: List[str] = Field(default=[], description="Jusqu'à 3 questions ciblées et courtes pour affiner l'estimation si floue")


class MealLoggingOnlyAnalysis(BaseModel):
    repas: str = Field(description="Type de repas: 'breakfast', 'lunch', 'dinner' ou 'snack'")
    aliments: List[Aliment] = Field(description="Liste des aliments identifiés")
    total_kcal: float = Field(description="Total des calories")
    total_proteines: float = Field(description="Total des protéines")
    total_glucides: float = Field(description="Total des glucides")
    total_lipides: float = Field(description="Total des lipides")
