from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Favourite

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class FavouriteCreate(BaseModel):
    food_name: str
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float

def _fav_dict(f):
    return {"id": f.id, "food_name": f.food_name, "calories": f.calories,
            "protein_g": f.protein_g, "carbs_g": f.carbs_g, "fat_g": f.fat_g}

@router.get("/")
def list_favourites(db: Session = Depends(get_db)):
    return [_fav_dict(f) for f in db.query(Favourite).order_by(Favourite.food_name).all()]

@router.post("/")
def create_favourite(body: FavouriteCreate, db: Session = Depends(get_db)):
    fav = Favourite(**body.model_dump())
    db.add(fav); db.commit(); db.refresh(fav)
    return _fav_dict(fav)

@router.delete("/{fav_id}")
def delete_favourite(fav_id: int, db: Session = Depends(get_db)):
    fav = db.query(Favourite).filter(Favourite.id == fav_id).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(fav); db.commit()
    return {"message": "Deleted"}
