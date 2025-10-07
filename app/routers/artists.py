from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.auth import require_admin, get_current_user

router = APIRouter()

@router.post("", response_model=schemas.ArtistOut, status_code=201, dependencies=[Depends(require_admin)])
def create_artist(payload: schemas.ArtistCreate, db: Session = Depends(get_db)):
    artist = models.Artist(name=payload.name)
    db.add(artist)
    db.commit()
    db.refresh(artist)
    return artist

@router.get("", response_model=list[schemas.ArtistOut])
def list_artists(db: Session = Depends(get_db)):
    return db.query(models.Artist).all()