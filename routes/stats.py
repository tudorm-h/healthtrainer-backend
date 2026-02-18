from datetime import date, timedelta, datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Meal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/weekly")
def weekly_stats(days: int = Query(default=7, ge=1, le=90), db: Session = Depends(get_db)):
    today = date.today()
    since = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) - timedelta(days=days-1)
    meals = db.query(Meal).filter(Meal.timestamp >= since).all()
    daily = {}
    for meal in meals:
        if not meal.timestamp: continue
        dk = meal.timestamp.date().isoformat()
        if dk not in daily:
            daily[dk] = {"date": dk, "calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "meal_count": 0}
        daily[dk]["calories"] += meal.calories or 0
        daily[dk]["protein_g"] += meal.protein_g or 0
        daily[dk]["carbs_g"] += meal.carbs_g or 0
        daily[dk]["fat_g"] += meal.fat_g or 0
        daily[dk]["meal_count"] += 1
    result = [(today - timedelta(days=days-1-i)).isoformat() for i in range(days)]
    result = [daily.get(d, {"date": d, "calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "meal_count": 0}) for d in result]
    all_days = {m.timestamp.date() for m in db.query(Meal).all() if m.timestamp}
    streak, check = 0, today
    while check in all_days:
        streak += 1; check -= timedelta(days=1)
    return {"days": result, "streak": streak}
