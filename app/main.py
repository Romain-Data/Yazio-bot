from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import os
import json
from typing import Optional
from app.services.mammouth_service import MammouthService, RepasAnalysis
from app.services.yazio_service import YazioService


app = FastAPI(title="Yazio Telegram Bot API")

mammouth_service = MammouthService()
yazio_service = YazioService()


def enrich_with_yazio(analysis: RepasAnalysis) -> RepasAnalysis:
    if analysis.is_creation_recette or analysis.is_creation_equivalence:
        return analysis

    for aliment in analysis.aliments:
        if getattr(aliment, "is_recipe", False):
            recipe_match = yazio_service.search_recipe(aliment.nom)
            if recipe_match:
                aliment.yazio_name = recipe_match["name"]
            else:
                aliment.yazio_name = "Recette non trouvée"
        else:
            search_res = yazio_service.search_products(aliment.nom)
            if search_res:
                aliment.yazio_name = search_res[0]["name"]
            else:
                aliment.yazio_name = "Produit non trouvé"
    return analysis


class TextAnalyzeRequest(BaseModel):
    text: str
    local_time: Optional[str] = None


class LogFoodRequest(BaseModel):
    analysis: RepasAnalysis


class CorrectionRequest(BaseModel):
    original_analysis: RepasAnalysis
    correction: str
    local_time: Optional[str] = None


@app.post("/analyze/text", response_model=RepasAnalysis)
async def analyze_text(request: TextAnalyzeRequest):
    """
    Analyzes a text description of a meal using Gemini AI.
    Returns the estimated nutritional values and the type of meal.
    """
    try:
        analysis = mammouth_service.analyze_text(request.text, request.local_time)
        return enrich_with_yazio(analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/image", response_model=RepasAnalysis)
async def analyze_image(
    file: Optional[UploadFile] = File(None),
    data: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(""),
    local_time: Optional[str] = Form(None)
):
    """
    Analyzes an image of a meal using Gemini AI, optionally assisted by a text description.
    Accepts the image in either the 'file' or 'data' form field to ensure compatibility with n8n.
    """
    try:
        uploaded_file = file or data
        if not uploaded_file:
            raise HTTPException(status_code=422, detail="No image file provided in 'file' or 'data' field.")

        content = await uploaded_file.read()
        analysis = mammouth_service.analyze_image(content, uploaded_file.content_type, text, local_time)
        return enrich_with_yazio(analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/correction", response_model=RepasAnalysis)
async def analyze_correction(request: CorrectionRequest):
    """
    Applies a natural language correction to a previous nutritional analysis.
    For example: "I actually ate 200g of pasta, not 100g."
    """
    try:
        analysis = mammouth_service.analyze_correction(
            request.original_analysis,
            request.correction,
            request.local_time
        )
        return enrich_with_yazio(analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/log")
async def log_food(request: LogFoodRequest):
    """
    Logs the analyzed meal items to the user's Yazio diary.
    Distinguishes between personal recipes and generic products.
    """
    try:
        if request.analysis.is_creation_equivalence:
            eq_key = request.analysis.equivalence_key or "Inconnu"
            eq_val = request.analysis.equivalence_value or "0g"
            
            weights_file = os.path.join(os.path.dirname(__file__), "data", "custom_weights.json")
            data = {}
            if os.path.exists(weights_file):
                try:
                    with open(weights_file, "r") as f:
                        data = json.load(f)
                except Exception:
                    pass
            
            data[eq_key] = eq_val
            
            with open(weights_file, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            return {
                "status": "success",
                "results": [
                    {
                        "aliment": f"Équivalence : {eq_key}",
                        "status": "logged",
                        "yazio_name": f"Ajoutée avec succès ({eq_val})",
                        "type": "equivalence créée"
                    }
                ]
            }
        if request.analysis.is_creation_recette:
            recipe_name = request.analysis.nom_recette or "Recette personnalisée"
            portions = request.analysis.portions or 1
            macros = yazio_service.create_recipe(recipe_name, portions, request.analysis.aliments)
            
            kcal_p = round(macros.get("energy.energy", 0) / portions)
            prot_p = round(macros.get("nutrient.protein", 0) / portions, 1)
            gluc_p = round(macros.get("nutrient.carb", 0) / portions, 1)
            lip_p = round(macros.get("nutrient.fat", 0) / portions, 1)
            
            macro_str = f"Créée avec succès ({portions} portion(s) - 1 part = {kcal_p} kcal | P:{prot_p}g | G:{gluc_p}g | L:{lip_p}g)"
            
            return {
                "status": "success",
                "results": [
                    {
                        "aliment": f"Recette : {recipe_name}",
                        "status": "logged",
                        "yazio_name": macro_str,
                        "type": "recette créée"
                    }
                ]
            }

        results = []
        for aliment in request.analysis.aliments:
            if getattr(aliment, "is_recipe", False):
                recipe_match = yazio_service.search_recipe(aliment.nom)
                if not recipe_match:
                    results.append({"aliment": aliment.nom, "status": "not_found", "type": "recette personnelle"})
                    continue

                total_recipe_portions = recipe_match["portion_count"]
                total_recipe_weight_g = recipe_match["total_weight"]

                fraction_eaten = aliment.quantite_g / total_recipe_weight_g
                portions_to_log = round(fraction_eaten * total_recipe_portions, 2)

                yazio_service.log_recipe(
                    recipe_id=recipe_match["recipe_id"],
                    portion_count=portions_to_log,
                    daytime=request.analysis.repas
                )
                results.append({"aliment": aliment.nom, "status": "logged", "yazio_name": recipe_match["name"], "type": "recette"})
            else:
                search_res = yazio_service.search_products(aliment.nom)
                if not search_res:
                    results.append({"aliment": aliment.nom, "status": "not_found", "type": "produit générique"})
                    continue

                best_match = search_res[0]
                product_id = best_match["product_id"]

                yazio_service.log_food(
                    product_id=product_id,
                    amount=aliment.quantite_g,
                    serving="g",
                    serving_quantity=aliment.quantite_g,
                    daytime=request.analysis.repas
                )
                results.append({"aliment": aliment.nom, "status": "logged", "yazio_name": best_match["name"], "type": "produit"})

        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok"}
