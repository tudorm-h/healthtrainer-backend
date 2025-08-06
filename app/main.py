from fastapi import FastAPI
from app.routes import upload
from app.database import init_db
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()
init_db()

# ✅ Add this line to serve image files
app.mount("/images", StaticFiles(directory="uploaded_images"), name="images")

app.include_router(upload.router, prefix="/upload", tags=["Upload"])

@app.get("/")
def read_root():
    return {"message": "API is running!"}
