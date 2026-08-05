from app.services.extractors.base_extractor import BaseExtractor
from app.models.analysis import RecipeCreationOnlyAnalysis, RepasAnalysis


class RecipeExtractor(BaseExtractor):
    def analyze_text(self, text: str, local_time: str) -> RepasAnalysis:
        prompt = f"""
        Tu es un expert en nutrition et en cuisine. L'utilisateur veut enregistrer une nouvelle recette.
        "{text}"

        L'heure locale est : {local_time or 'inconnue'}.

        Extrais le nom de la recette, le nombre de portions si précisé (sinon 1), et la liste des ingrédients composant cette recette avec leurs quantités et valeurs nutritionnelles.

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {RecipeCreationOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, RecipeCreationOnlyAnalysis)
        return RepasAnalysis(
            repas="snack",
            aliments=res.ingredients,
            total_kcal=0,
            total_proteines=0,
            total_glucides=0,
            total_lipides=0,
            is_creation_recette=True,
            nom_recette=res.nom_recette,
            portions=res.portions
        )

    def analyze_correction(self, original_analysis: RepasAnalysis, correction: str, local_time: str) -> RepasAnalysis:
        orig_recipe = RecipeCreationOnlyAnalysis(
            nom_recette=original_analysis.nom_recette or "Recette personnalisée",
            portions=original_analysis.portions or 1,
            ingredients=original_analysis.aliments or []
        )
        prompt = f"""
        Tu es un expert en nutrition. Voici l'analyse de la création de la recette précédente :
        {orig_recipe.model_dump_json()}

        L'utilisateur demande la correction suivante :
        "{correction}"

        L'heure locale est : {local_time or 'inconnue'}.

        Modifie l'analyse originale de la recette en prenant en compte la correction de l'utilisateur (nom de la recette, portions, ou ingrédients).

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {RecipeCreationOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, RecipeCreationOnlyAnalysis)
        return RepasAnalysis(
            repas="snack",
            aliments=res.ingredients,
            total_kcal=0,
            total_proteines=0,
            total_glucides=0,
            total_lipides=0,
            is_creation_recette=True,
            nom_recette=res.nom_recette,
            portions=res.portions
        )
