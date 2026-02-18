from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import upload, water, favourites, barcode, stats
from database import init_db

app = FastAPI(title="HealthTrainer API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
init_db()
app.mount("/images", StaticFiles(directory="uploaded_images"), name="images")
app.include_router(upload.router, prefix="/upload", tags=["Meals"])
app.include_router(water.router, prefix="/water", tags=["Water"])
app.include_router(favourites.router, prefix="/favourites", tags=["Favourites"])
app.include_router(barcode.router, prefix="/barcode", tags=["Barcode"])
app.include_router(stats.router, prefix="/stats", tags=["Stats"])

@app.get("/")
def read_root():
    return {"message": "HealthTrainer API running"}
