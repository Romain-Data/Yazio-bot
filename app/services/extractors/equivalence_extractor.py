from app.services.extractors.base_extractor import BaseExtractor
from app.models.analysis import EquivalenceOnlyAnalysis, RepasAnalysis


class EquivalenceExtractor(BaseExtractor):
    def analyze_text(self, text: str, local_time: str) -> RepasAnalysis:
        prompt = f"""
        Tu es un expert en nutrition. L'utilisateur veut enregistrer une nouvelle équivalence de poids pour un aliment.
        "{text}"

        L'heure locale est : {local_time or 'inconnue'}.

        Extrais l'aliment avec sa portion/unité dans `equivalence_key` (ex: '1 tranche de jambon') et le poids correspondant en grammes dans `equivalence_value` (ex: '40g').

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {EquivalenceOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, EquivalenceOnlyAnalysis)
        return RepasAnalysis(
            repas="snack",
            aliments=[],
            total_kcal=0,
            total_proteines=0,
            total_glucides=0,
            total_lipides=0,
            is_creation_equivalence=True,
            equivalence_key=res.equivalence_key,
            equivalence_value=res.equivalence_value
        )

    def analyze_correction(self, original_analysis: RepasAnalysis, correction: str, local_time: str) -> RepasAnalysis:
        orig_equiv = EquivalenceOnlyAnalysis(
            equivalence_key=original_analysis.equivalence_key or "1 portion",
            equivalence_value=original_analysis.equivalence_value or "0g"
        )
        prompt = f"""
        Tu es un expert en nutrition. Voici l'équivalence de poids précédente :
        {orig_equiv.model_dump_json()}

        L'utilisateur demande la correction suivante :
        "{correction}"

        L'heure locale est : {local_time or 'inconnue'}.

        Modifie l'équivalence originale en prenant en compte la correction de l'utilisateur (la clé de l'aliment ou le poids associé).

        Tu DOIS répondre UNIQUEMENT sous forme d'un objet JSON respectant exactement le schéma Pydantic suivant :
        {EquivalenceOnlyAnalysis.model_json_schema()}
        """
        res = self._call_api(prompt, EquivalenceOnlyAnalysis)
        return RepasAnalysis(
            repas="snack",
            aliments=[],
            total_kcal=0,
            total_proteines=0,
            total_glucides=0,
            total_lipides=0,
            is_creation_equivalence=True,
            equivalence_key=res.equivalence_key,
            equivalence_value=res.equivalence_value
        )
