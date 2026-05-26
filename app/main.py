from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.gemini_service import GeminiService, RepasAnalysis
from app.services.yazio_service import YazioService

app = FastAPI(title="Yazio Telegram Bot API")

gemini_service = GeminiService()
yazio_service = YazioService()

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
        return gemini_service.analyze_text(request.text, request.local_time)
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
        return gemini_service.analyze_image(content, uploaded_file.content_type, text, local_time)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/correction", response_model=RepasAnalysis)
async def analyze_correction(request: CorrectionRequest):
    """
    Applies a natural language correction to a previous nutritional analysis.
    For example: "I actually ate 200g of pasta, not 100g."
    """
    try:
        return gemini_service.analyze_correction(
            request.original_analysis, 
            request.correction, 
            request.local_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/log")
async def log_food(request: LogFoodRequest):
    """
    Logs the analyzed meal items to the user's Yazio diary.
    Distinguishes between personal recipes and generic products.
    """
    try:
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
