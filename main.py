from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import router as auth_router
from app.routers.music_items import router as music_router
from app.routers.reviews import router as reviews_router
from app.routers.collections import router as collections_router
from app.routers.artists import router as artists_router
from app.routers.genres import router as genres_router
from app.routers.track_files import router as track_files_router
from app.database import init_db
from contextlib import asynccontextmanager

app = FastAPI(title="Music Collection Manager", version="1.0.0")

# CORS (For real production we would restrict origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app.router.lifespan_context = lifespan

@app.get("/", tags=["meta"])
def root():
    return {"message": "Music Collection Manager API", "docs": "/docs"}

# Optional simple user management demo (header-based)
app.include_router(auth_router, prefix="/auth", tags=["auth-demo"])

# Core resources
app.include_router(music_router, prefix="/music-items", tags=["music-items"])
app.include_router(artists_router, prefix="/artists", tags=["artists"])
app.include_router(genres_router, prefix="/genres", tags=["genres"])
app.include_router(reviews_router, prefix="/reviews", tags=["reviews"])
app.include_router(collections_router, prefix="/users", tags=["collections"])
app.include_router(track_files_router, prefix="/files", tags=["track-files"])