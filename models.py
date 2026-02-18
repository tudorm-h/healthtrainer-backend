from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class Meal(Base):
    __tablename__ = "meals"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, unique=True)
    food_guess = Column(String)
    calories = Column(Integer)
    protein_g = Column(Float)
    carbs_g = Column(Float)
    fat_g = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    was_refined = Column(Boolean, default=False)
    refinement_context = Column(String, nullable=True)
    __table_args__ = (Index("ix_meals_timestamp", "timestamp"),)


class WaterLog(Base):
    __tablename__ = "water_log"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    amount_ml = Column(Integer, nullable=False)


class Favourite(Base):
    __tablename__ = "favourites"
    id = Column(Integer, primary_key=True, index=True)
    food_name = Column(String, nullable=False)
    calories = Column(Integer)
    protein_g = Column(Float)
    carbs_g = Column(Float)
    fat_g = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
