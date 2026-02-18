import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()
OFF_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

@router.get("/{barcode}")
async def lookup_barcode(barcode: str):
    if not barcode.isdigit() or not (8 <= len(barcode) <= 14):
        raise HTTPException(status_code=400, detail="Invalid barcode")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(OFF_URL.format(barcode=barcode))
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Open Food Facts unavailable")
    data = resp.json()
    if data.get("status") != 1:
        raise HTTPException(status_code=404, detail="Product not found")
    product = data["product"]
    nutriments = product.get("nutriments", {})
    serving_g = float(product.get("serving_quantity") or 100)
    scale = serving_g / 100.0
    def ps(key): return round(float(nutriments.get(f"{key}_100g") or nutriments.get(key) or 0) * scale, 1)
    return {"food_name": product.get("product_name") or "Unknown", "brand": product.get("brands", ""),
            "serving_g": serving_g, "calories": round(ps("energy-kcal")),
            "protein_g": ps("proteins"), "carbs_g": ps("carbohydrates"), "fat_g": ps("fat"), "barcode": barcode}
