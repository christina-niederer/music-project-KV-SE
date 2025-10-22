from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.core.auth import get_current_user

router = APIRouter()

@router.post("", response_model=schemas.ReviewOut, status_code=201)
def create_or_update_review(payload: schemas.ReviewCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    # Ensure item exists
    mi = db.get(models.MusicItem, payload.music_item_id)
    if not mi:
        raise HTTPException(status_code=404, detail="Music item not found")

    # Upsert: one review per (user,item)
    existing = db.query(models.Review).filter(
        models.Review.user_id == user.id,
        models.Review.music_item_id == payload.music_item_id
    ).one_or_none()

    if existing:
        existing.rating = payload.rating
        existing.text = payload.text
        db.commit()
        db.refresh(existing)
        return existing

    review = models.Review(user_id=user.id, music_item_id=payload.music_item_id,
                           rating=payload.rating, text=payload.text)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

@router.get("/item/{music_item_id}", response_model=list[schemas.ReviewOut])
def list_reviews_for_item(music_item_id: int, db: Session = Depends(get_db)):
    return db.query(models.Review).filter(
        models.Review.music_item_id == music_item_id
    ).options(
        joinedload(models.Review.user)
    ).all()

@router.delete("/{review_id}", status_code=204)
def delete_review(review_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    review = db.get(models.Review, review_id)
    if not review:
        return
    if review.user_id != user.id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Cannot delete others' reviews")
    db.delete(review)
    db.commit()
    return