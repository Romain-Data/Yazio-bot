from app.services.extractors.base_extractor import BaseExtractor
from app.models.analysis import ActivityOnlyAnalysis, RepasAnalysis


class ActivityExtractor(BaseExtractor):
    def analyze_text(self, text: str, local_time: str) -> RepasAnalysis:
        prompt = f"""
        Tu es un expert en nutrition et en entraînement sportif. L'utilisateur décrit l'activité physique suivante :
        "{text}"

        L'heure locale est : {local_time or 'inconnue'}.

        Estime la dépense calorique de l'utilisateur de manière TRÈS PRUDENTE et réaliste (pour un adulte de 75 kg) en respectant les repères suivants :
        - Activité faible / de loisir (ex: jouer dans l'eau avec des enfants, marche tranquille, rangement/jardinage) : environ 2,5 à 3 kcal/min (soit ~150-180 kcal/heure). Par exemple, pour 3h de jeu en piscine, cela représente environ 400 à 450 kcal maximum (en comptant les pauses).
        - Activité modérée (ex: tennis de table, vélo tranquille, jeux de ballons actifs) : environ 5 à 6 kcal/min (soit ~300-360 kcal/heure).
        - Activité intense / sport soutenu (ex: tennis match, footing, natation active continue) : environ 8 à 10 kcal/min (soit ~480-600 kcal/heure).

        DURÉE DE L'EFFORT RÉEL (TRÈS IMPORTANT) :
        La durée de l'activité `duree_minutes` doit correspondre uniquement au temps d'effort physique réel et actif. N'inclus pas les temps de repos passifs ou de simple présence sur place (par exemple si l'utilisateur dit "5h passés là-bas dont 3h dans l'eau", retiens 3h soit 180 minutes).

        QUESTIONS D'AFFINAGE :
        Si la description contient des termes flous quant à l'intensité ou les conditions (ex: "piscine avec les enfants", "vélo en famille"), tu DOIS impérativement poser jusqu'à 3 questions courtes et polies dans la liste `questions` pour affiner (ex: "S'agissait-il de natation continue ou plutôt de jeux calmes dans l'eau ?", "Y a-t-il eu des temps de repos durant ces 3 heures ?") ET retenir l'estimation basse par défaut. Laisse la liste `questions` vide si tout est déjà très clair.

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {ActivityOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, ActivityOnlyAnalysis)
        return RepasAnalysis(
            repas="snack",
            aliments=[],
            total_kcal=0,
            total_proteines=0,
            total_glucides=0,
            total_lipides=0,
            is_activity=True,
            nom_activite=res.nom_activite,
            duree_minutes=res.duree_minutes,
            calories_brules=res.calories_brules,
            questions=res.questions
        )

    def analyze_correction(self, original_analysis: RepasAnalysis, correction: str, local_time: str) -> RepasAnalysis:
        orig_act = ActivityOnlyAnalysis(
            nom_activite=original_analysis.nom_activite or "Activité physique",
            duree_minutes=original_analysis.duree_minutes or 0,
            calories_brules=original_analysis.calories_brules or 0.0,
            questions=original_analysis.questions or []
        )
        prompt = f"""
        Tu es un expert en entraînement sportif. Voici l'analyse de l'activité physique que tu avais précédemment estimée :
        {orig_act.model_dump_json()}

        L'utilisateur demande la correction ou répond aux questions d'affinage avec le message suivant :
        "{correction}"

        L'heure locale est : {local_time or 'inconnue'}.

        Modifie l'analyse originale en prenant en compte la correction de l'utilisateur.
        Ajuste `nom_activite`, `duree_minutes` et `calories_brules` en fonction des réponses ou corrections de l'utilisateur, en restant très réaliste et prudent (ex: 2.5-3 kcal/min pour loisir/jeux, 5-6 kcal/min pour modéré, 8-10 kcal/min pour intense).

        DURÉE DE L'EFFORT RÉEL (TRÈS IMPORTANT) :
        La durée de l'activité `duree_minutes` doit correspondre uniquement au temps d'effort physique réel et actif. Si l'utilisateur mentionne une durée totale sur place avec des temps de repos ou précise un temps actif partiel (ex: 'On a passé 5h à la piscine dont 3h dans l'eau', '2h de vélo dont 30min de pause'), tu DOIS impérativement utiliser uniquement la durée de l'effort physique effectif (ici, 3h soit 180 minutes, ou 1h30 soit 90 minutes) pour la variable `duree_minutes` et estimer les calories en conséquence.

        Si l'utilisateur a répondu aux questions d'affinage précédentes pour l'activité, prends en compte ses réponses pour ajuster la dépense calorique de manière précise, puis retire ces questions résolues de la liste `questions`. S'il reste des incertitudes majeures, tu peux formuler de nouvelles questions d'affinage (maximum 3 au total). Si l'estimation est désormais assez précise, laisse la liste `questions` vide.

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {ActivityOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, ActivityOnlyAnalysis)
        return RepasAnalysis(
            repas="snack",
            aliments=[],
            total_kcal=0,
            total_proteines=0,
            total_glucides=0,
            total_lipides=0,
            is_activity=True,
            nom_activite=res.nom_activite,
            duree_minutes=res.duree_minutes,
            calories_brules=res.calories_brules,
            questions=res.questions
        )
