from datetime import date
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from models import WaterLog

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class WaterUpdate(BaseModel):
    amount_ml: int

@router.get("/")
def get_water(day: str | None = None, db: Session = Depends(get_db)):
    target_date = date.fromisoformat(day) if day else date.today()
    log = db.query(WaterLog).filter(WaterLog.date == target_date).first()
    return {"date": str(target_date), "amount_ml": log.amount_ml if log else 0}

@router.post("/")
def set_water(body: WaterUpdate, db: Session = Depends(get_db)):
    today = date.today()
    log = db.query(WaterLog).filter(WaterLog.date == today).first()
    if log:
        log.amount_ml = body.amount_ml
    else:
        log = WaterLog(date=today, amount_ml=body.amount_ml)
        db.add(log)
    db.commit()
    return {"date": str(today), "amount_ml": log.amount_ml}
