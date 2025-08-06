import os
import shutil
import base64
import json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from openai import OpenAI
from database import SessionLocal
from app.models import Meal

router = APIRouter()
load_dotenv()

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# GET /upload/ to fetch all meals
@router.get("/")
def read_meals(db: Session = Depends(get_db)):
    meals = db.query(Meal).order_by(Meal.timestamp.desc()).all()
    return [
        {
            "filename": meal.filename,
            "food_guess": meal.food_guess,
            "calories": meal.calories,
            "protein_g": meal.protein_g,
            "carbs_g": meal.carbs_g,
            "fat_g": meal.fat_g,
            "timestamp": meal.timestamp.isoformat(),
        }
        for meal in meals
    ]

# POST /upload/ to upload and analyse image
@router.post("/")
async def upload_image(
    file: UploadFile = File(...),
    context: str = Form(default="")
):
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"Saved file to {file_path}")

        with open(file_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        base_prompt = (
            "You're a nutritionist. Identify the food in this photo "
            "and respond ONLY with valid JSON in this format:\n"
            "{\n"
            "  \"food_guess\": \"\",\n"
            "  \"calories\": 0,\n"
            "  \"protein_g\": 0,\n"
            "  \"carbs_g\": 0,\n"
            "  \"fat_g\": 0\n"
            "}"
        )

        full_prompt = base_prompt
        if context.strip():
            full_prompt += f"\n\nAdditional context from the user: \"{context.strip()}\""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                    ],
                }
            ],
            max_tokens=300,
            temperature=0.2,
        )

        gpt_output = response.choices[0].message.content.strip()
        print("GPT Output:\n", gpt_output)

        if gpt_output.startswith("```"):
            gpt_output = gpt_output.strip("```json").strip("```").strip()

        result = json.loads(gpt_output)
        result["filename"] = filename

        db = SessionLocal()
        try:
            meal = Meal(
                filename=filename,
                food_guess=result["food_guess"],
                calories=result["calories"],
                protein_g=result["protein_g"],
                carbs_g=result["carbs_g"],
                fat_g=result["fat_g"],
            )
            db.add(meal)
            db.commit()
        finally:
            db.close()

        return JSONResponse(content=result)

    except Exception as e:
        print("AI processing failed:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)
