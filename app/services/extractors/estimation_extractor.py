from app.services.extractors.base_extractor import BaseExtractor
from app.models.analysis import GlobalEstimationOnlyAnalysis, RepasAnalysis, Aliment


class EstimationExtractor(BaseExtractor):
    def analyze_text(self, text: str, local_time: str) -> RepasAnalysis:
        prompt = f"""
        Tu es un expert en nutrition. L'utilisateur demande une estimation globale pour un repas décrit de manière floue ou générale :
        "{text}"

        L'heure locale est : {local_time or 'inconnue'}.

        Estime les calories et macronutriments pour l'ensemble du repas.
        Déduis le type de repas (breakfast, lunch, snack, dinner) en fonction de l'heure ou de la description.
        ATTENTION : Si l'utilisateur précise explicitement le type de repas dans son message (ex: "petit déjeuner", "déjeuner", "dîner", "snack", "goûter"), tu DOIS utiliser cette information en priorité absolue.
        Rédige dans la liste `questions` jusqu'à 3 questions ciblées et courtes en français pour aider à affiner l'estimation si elle est floue (ex: présence de sauce/huile, portion petite/normale/grande, ingrédients clés, type de viande/cuisson). Laisse la liste `questions` vide si l'estimation est déjà très précise ou si aucune question n'est nécessaire.

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {GlobalEstimationOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, GlobalEstimationOnlyAnalysis)

        repas = res.repas
        if not repas or repas not in ["breakfast", "lunch", "dinner", "snack"]:
            repas = "snack"
            if local_time:
                try:
                    hour = int(local_time.split("T")[1].split(":")[0])
                    if 5 <= hour < 11:
                        repas = "breakfast"
                    elif 11 <= hour < 15:
                        repas = "lunch"
                    elif 18 <= hour < 23:
                        repas = "dinner"
                except Exception:
                    pass

        virtual_aliment = Aliment(
            nom=res.nom_estimation,
            quantite_g=1.0,
            kcal=res.total_kcal,
            proteines=res.total_proteines,
            glucides=res.total_glucides,
            lipides=res.total_lipides,
            is_recipe=False
        )

        return RepasAnalysis(
            repas=repas,
            aliments=[virtual_aliment],
            total_kcal=res.total_kcal,
            total_proteines=res.total_proteines,
            total_glucides=res.total_glucides,
            total_lipides=res.total_lipides,
            is_estimation=True,
            nom_estimation=res.nom_estimation,
            questions=res.questions
        )

    def analyze_image(self, image_part: dict, text: str, local_time: str) -> RepasAnalysis:
        prompt = f"""
        Tu es un expert en nutrition. L'utilisateur a pris une photo de son repas et demande une estimation globale.
        {f'Il a ajouté le commentaire suivant : "{text}"' if text else ''}

        L'heure locale est : {local_time or 'inconnue'}.

        Estime les calories et macronutriments pour l'ensemble du repas à partir de la photo et du commentaire.
        Déduis le type de repas (breakfast, lunch, snack, dinner) en fonction de l'heure, des aliments ou du commentaire.
        ATTENTION : Si l'utilisateur précise explicitement le type de repas dans son commentaire/message (ex: "petit déjeuner", "déjeuner", "dîner", "snack", "goûter"), tu DOIS utiliser cette information en priorité absolue.
        Rédige dans la liste `questions` jusqu'à 3 questions ciblées et courtes en français pour aider à affiner l'estimation si elle est floue. Laisse la liste `questions` vide si l'estimation est déjà très précise.

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {GlobalEstimationOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, GlobalEstimationOnlyAnalysis, image_part)

        repas = res.repas
        if not repas or repas not in ["breakfast", "lunch", "dinner", "snack"]:
            repas = "snack"
            if local_time:
                try:
                    hour = int(local_time.split("T")[1].split(":")[0])
                    if 5 <= hour < 11:
                        repas = "breakfast"
                    elif 11 <= hour < 15:
                        repas = "lunch"
                    elif 18 <= hour < 23:
                        repas = "dinner"
                except Exception:
                    pass

        virtual_aliment = Aliment(
            nom=res.nom_estimation,
            quantite_g=1.0,
            kcal=res.total_kcal,
            proteines=res.total_proteines,
            glucides=res.total_glucides,
            lipides=res.total_lipides,
            is_recipe=False
        )

        return RepasAnalysis(
            repas=repas,
            aliments=[virtual_aliment],
            total_kcal=res.total_kcal,
            total_proteines=res.total_proteines,
            total_glucides=res.total_glucides,
            total_lipides=res.total_lipides,
            is_estimation=True,
            nom_estimation=res.nom_estimation,
            questions=res.questions
        )

    def analyze_correction(self, original_analysis: RepasAnalysis, correction: str, local_time: str) -> RepasAnalysis:
        orig_est = GlobalEstimationOnlyAnalysis(
            repas=original_analysis.repas or "snack",
            nom_estimation=original_analysis.nom_estimation or "Estimation",
            total_kcal=original_analysis.total_kcal,
            total_proteines=original_analysis.total_proteines,
            total_glucides=original_analysis.total_glucides,
            total_lipides=original_analysis.total_lipides,
            questions=original_analysis.questions or []
        )
        prompt = f"""
        Tu es un expert en nutrition. Voici l'estimation globale précédente :
        {orig_est.model_dump_json()}

        L'utilisateur demande la correction suivante ou répond aux questions d'affinage :
        "{correction}"

        L'heure locale est : {local_time or 'inconnue'}.

        Modifie l'estimation originale en prenant en compte les corrections ou réponses de l'utilisateur.
        Ajuste le nom de l'estimation et les valeurs de calories/macronutriments en conséquence.
        Conserve ou adapte le type de repas (breakfast, lunch, snack, dinner).
        ATTENTION : Si l'utilisateur précise explicitement le type de repas dans sa correction (ex: "C'est un petit déjeuner", "dîner", etc.), tu DOIS mettre à jour le type de repas.
        Si l'utilisateur a répondu aux questions d'affinage précédentes, utilise ses réponses pour affiner et retire ces questions résolues. Si l'estimation est désormais assez précise, laisse la liste `questions` vide. S'il reste des incertitudes majeures, tu peux formuler de nouvelles questions d'affinage (maximum 3).

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {GlobalEstimationOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, GlobalEstimationOnlyAnalysis)

        virtual_aliment = Aliment(
            nom=res.nom_estimation,
            quantite_g=1.0,
            kcal=res.total_kcal,
            proteines=res.total_proteines,
            glucides=res.total_glucides,
            lipides=res.total_lipides,
            is_recipe=False
        )

        return RepasAnalysis(
            repas=res.repas or original_analysis.repas or "snack",
            aliments=[virtual_aliment],
            total_kcal=res.total_kcal,
            total_proteines=res.total_proteines,
            total_glucides=res.total_glucides,
            total_lipides=res.total_lipides,
            is_estimation=True,
            nom_estimation=res.nom_estimation,
            questions=res.questions
        )
