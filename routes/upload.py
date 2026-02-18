import os
import io
import re
import shutil
import base64
import json
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

from database import SessionLocal
from models import Meal

router = APIRouter()
load_dotenv()

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_PX = 800  # Max width/height before resizing
MAX_FILE_MB = 10

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def compress_image(file_bytes: bytes, max_px: int = MAX_IMAGE_PX) -> bytes:
    """Resize image so its longest side <= max_px, then re-encode as JPEG.
    This dramatically reduces base64 payload size sent to GPT-4o."""
    img = Image.open(io.BytesIO(file_bytes))
    img = img.convert("RGB")  # Ensure no alpha channel issues with JPEG
    w, h = img.size
    if max(w, h) > max_px:
        scale = max_px / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()


def strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences from GPT output."""
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()


# GET /upload/ — fetch saved meals with pagination
@router.get("/")
def read_meals(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    meals = (
        db.query(Meal)
        .order_by(Meal.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
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


# POST /upload/ — upload and analyse a meal image
@router.post("/")
async def upload_image(
    file: UploadFile = File(...),
    context: str = Form(default=""),
    db: Session = Depends(get_db),  # Fixed: use DI instead of manual SessionLocal()
):
    # --- Validate file type ---
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Upload a JPEG, PNG or WebP image.",
        )

    # --- Read & enforce size limit ---
    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_FILE_MB} MB limit.",
        )

    try:
        # --- Compress / resize before saving and sending to GPT ---
        compressed = compress_image(raw_bytes)

        # Save compressed version to disk
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(compressed)
        print(f"Saved compressed file to {file_path} ({len(compressed)//1024}KB)")

        # Encode compressed image to base64
        encoded_image = base64.b64encode(compressed).decode("utf-8")

        # --- Compose prompt ---
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

        # --- Call OpenAI with timeout (updated to v1 SDK) ---
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
            timeout=30,
        )

        gpt_output = response.choices[0].message.content.strip()
        print("GPT Output:\n", gpt_output)

        # --- Clean fences and parse JSON ---
        gpt_clean = strip_code_fences(gpt_output)
        try:
            result = json.loads(gpt_clean)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=502, detail=f"GPT returned invalid JSON: {e}")

        result["filename"] = filename

        # --- Save to DB (uses injected session, no manual SessionLocal) ---
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

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        print("Processing failed:", e)
        raise HTTPException(status_code=500, detail=str(e))


# DELETE /upload/meals/{filename}
@router.delete("/meals/{filename}")
def delete_meal(filename: str, db: Session = Depends(get_db)):
    # Step 1: Check DB record exists first (fail fast before touching filesystem)
    meal = db.query(Meal).filter(Meal.filename == filename).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found in database")

    # Step 2: Delete DB record
    db.delete(meal)
    db.commit()
    print(f"Deleted DB record for: {filename}")

    # Step 3: Delete image file (best-effort — don't fail if already missing)
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted file: {file_path}")
    else:
        print(f"File not found on disk (already deleted?): {file_path}")

    return {"message": f"{filename} deleted successfully"}
