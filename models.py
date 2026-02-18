from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    food_guess = Column(String)
    calories = Column(Integer)
    protein_g = Column(Float)
    carbs_g = Column(Float)
    fat_g = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Index on timestamp for fast ordered queries
    __table_args__ = (
        Index("ix_meals_timestamp", "timestamp"),
    )
