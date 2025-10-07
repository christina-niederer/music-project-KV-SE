from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.core.auth import require_admin

router = APIRouter()

@router.post("", response_model=schemas.GenreOut, status_code=201, dependencies=[Depends(require_admin)])
def create_genre(payload: schemas.GenreCreate, db: Session = Depends(get_db)):
    genre = models.Genre(name=payload.name)
    db.add(genre)
    db.commit()
    db.refresh(genre)
    return genre

@router.get("", response_model=list[schemas.GenreOut])
def list_genres(db: Session = Depends(get_db)):
    return db.query(models.Genre).all()