from app.services.extractors.base_extractor import BaseExtractor
from app.models.analysis import MealLoggingOnlyAnalysis, RepasAnalysis


class MealExtractor(BaseExtractor):
    def analyze_text(self, text: str, local_time: str, custom_weights_str: str) -> RepasAnalysis:
        prompt = f"""
        Tu es un expert en nutrition. L'utilisateur vient de manger le repas suivant :
        "{text}"

        L'heure locale est : {local_time or 'inconnue'}.

        Estime les valeurs nutritionnelles de chaque aliment décrit.
        Déduis le type de repas (breakfast, lunch, snack, dinner) en fonction de l'heure ou de la description.
        ATTENTION : Si l'utilisateur précise explicitement le type de repas dans son message (ex: "petit déjeuner", "déjeuner", "dîner", "snack", "goûter"), tu DOIS utiliser cette information en priorité absolue.
        ATTENTION RECETTE : Si l'utilisateur précise "(recette)" à côté d'un aliment, passe la valeur `is_recipe` à `true` pour cet aliment, et retire la mention "(recette)" de son nom. Sinon laisse à `false`.

        EQUIVALENCES DE POIDS PERSONNALISÉES (TRÈS IMPORTANT) :
        Voici une table de correspondance de poids que tu DOIS ABSOLUMENT utiliser pour tes conversions si l'aliment correspond sémantiquement.
        Cependant, si l'utilisateur précise un poids exact en grammes dans son message (ex: "jambon 60g"), ce poids exact a toujours la priorité absolue sur la table.
        {custom_weights_str}

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {MealLoggingOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, MealLoggingOnlyAnalysis)
        return RepasAnalysis(
            repas=res.repas,
            aliments=res.aliments,
            total_kcal=res.total_kcal,
            total_proteines=res.total_proteines,
            total_glucides=res.total_glucides,
            total_lipides=res.total_lipides
        )

    def analyze_image(self, image_part: dict, text: str, local_time: str, custom_weights_str: str) -> RepasAnalysis:
        prompt = f"""
        Tu es un expert en nutrition. L'utilisateur a pris une photo de son repas.
        {f'Il a ajouté le commentaire suivant : "{text}"' if text else ''}

        L'heure locale est : {local_time or 'inconnue'}.

        Identifie les aliments sur la photo, estime leurs portions (en grammes) et leurs valeurs nutritionnelles.
        Déduis le type de repas (breakfast, lunch, snack, dinner) en fonction de l'heure ou des aliments.
        ATTENTION : Si l'utilisateur précise explicitement le type de repas dans son message (ex: "petit déjeuner", "déjeuner", "dîner", "snack", "goûter"), tu DOIS utiliser cette information en priorité absolue.
        ATTENTION RECETTE : Si l'utilisateur précise "(recette)" à côté d'un aliment, passe la valeur `is_recipe` à `true` pour cet aliment, et retire la mention "(recette)" de son nom. Sinon laisse à `false`.

        EQUIVALENCES DE POIDS PERSONNALISÉES (TRÈS IMPORTANT) :
        Voici une table de correspondance de poids que tu DOIS ABSOLUMENT utiliser pour tes conversions si l'aliment correspond sémantiquement.
        Cependant, si l'utilisateur précise un poids exact en grammes dans son message (ex: "jambon 60g"), ce poids exact a toujours la priorité absolue sur la table.
        {custom_weights_str}

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {MealLoggingOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, MealLoggingOnlyAnalysis, image_part)
        return RepasAnalysis(
            repas=res.repas,
            aliments=res.aliments,
            total_kcal=res.total_kcal,
            total_proteines=res.total_proteines,
            total_glucides=res.total_glucides,
            total_lipides=res.total_lipides
        )

    def analyze_correction(self, original_analysis: RepasAnalysis, correction: str, local_time: str, custom_weights_str: str) -> RepasAnalysis:
        orig_meal = MealLoggingOnlyAnalysis(
            repas=original_analysis.repas,
            aliments=original_analysis.aliments,
            total_kcal=original_analysis.total_kcal,
            total_proteines=original_analysis.total_proteines,
            total_glucides=original_analysis.total_glucides,
            total_lipides=original_analysis.total_lipides
        )
        prompt = f"""
        Tu es un expert en nutrition. Voici l'analyse nutritionnelle du repas que tu avais précédemment estimée :
        {orig_meal.model_dump_json()}

        L'utilisateur demande la correction suivante :
        "{correction}"

        L'heure locale est : {local_time or 'inconnue'}.

        Modifie l'analyse originale en prenant en compte la correction de l'utilisateur (ajoute, supprime ou modifie les quantités des aliments).
        Conserve ou adapte le type de repas (breakfast, lunch, snack, dinner).
        ATTENTION : Si l'utilisateur précise explicitement le type de repas dans sa correction (ex: "C'est un petit déjeuner", "dîner", etc.), tu DOIS mettre à jour le type de repas.
        ATTENTION RECETTE : Si l'utilisateur précise "(recette)" à côté d'un aliment corrigé ou ajouté, passe la valeur `is_recipe` à `true` pour cet aliment, et retire la mention "(recette)" de son nom.

        EQUIVALENCES DE POIDS PERSONNALISÉES (TRÈS IMPORTANT) :
        Voici une table de correspondance de poids que tu DOIS ABSOLUMENT utiliser pour tes conversions si l'aliment correspond sémantiquement.
        Cependant, si l'utilisateur précise un poids exact en grammes dans sa correction (ex: "jambon 60g"), ce poids exact a toujours la priorité absolue sur la table.
        {custom_weights_str}

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {MealLoggingOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, MealLoggingOnlyAnalysis)
        return RepasAnalysis(
            repas=res.repas,
            aliments=res.aliments,
            total_kcal=res.total_kcal,
            total_proteines=res.total_proteines,
            total_glucides=res.total_glucides,
            total_lipides=res.total_lipides
        )
