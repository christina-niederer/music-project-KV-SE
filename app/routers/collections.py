from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app import models, schemas
from app.core.auth import get_current_user

router = APIRouter()

# /users/{user_id}/collection
def _serialize_collection_entry(entry: models.UserCollection) -> schemas.CollectionEntryOut:
    mi = entry.music_item
    # Reused logic similar to music_items.serialize_music_item (to avoid circular import)
    from app.routers.music_items import serialize_music_item  # local import to prevent cycles
    enriched = serialize_music_item(mi)
    return schemas.CollectionEntryOut(
        user_id=entry.user_id,
        music_item_id=entry.music_item_id,
        preference=entry.preference,
        is_favourite=entry.is_favourite,
        note=entry.note,
        music_item=enriched,
    )

@router.get("/{user_id}/collection", response_model=list[schemas.CollectionEntryOut])
def get_collection(user_id: int, db: Session = Depends(get_db)):
    entries = db.query(models.UserCollection).options(
        selectinload(models.UserCollection.music_item).selectinload(models.MusicItem.artists).selectinload(models.MusicItemArtist.artist),
        selectinload(models.UserCollection.music_item).selectinload(models.MusicItem.genres).selectinload(models.MusicItemGenre.genre),
        selectinload(models.UserCollection.music_item).selectinload(models.MusicItem.album_tracks).selectinload(models.AlbumTrack.track).selectinload(models.MusicItem.artists).selectinload(models.MusicItemArtist.artist),
        selectinload(models.UserCollection.music_item).selectinload(models.MusicItem.album_tracks).selectinload(models.AlbumTrack.track).selectinload(models.MusicItem.genres).selectinload(models.MusicItemGenre.genre),
    ).filter(models.UserCollection.user_id == user_id).all()
    return [_serialize_collection_entry(e) for e in entries]

@router.post("/{user_id}/collection/{music_item_id}", status_code=201)
def add_to_collection(user_id: int, music_item_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if user.id != user_id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Cannot modify another user's collection")
    if not db.get(models.MusicItem, music_item_id):
        raise HTTPException(status_code=404, detail="Music item not found")

    existing = db.query(models.UserCollection).filter_by(user_id=user_id, music_item_id=music_item_id).one_or_none()
    if existing:
        return existing
    entry = models.UserCollection(user_id=user_id, music_item_id=music_item_id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

@router.patch("/{user_id}/collection/{music_item_id}")
def update_collection_entry(user_id: int, music_item_id: int, payload: schemas.CollectionUpsert,
                            db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if user.id != user_id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Cannot modify another user's collection")
    entry = db.query(models.UserCollection).filter_by(user_id=user_id, music_item_id=music_item_id).one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Collection entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry

@router.delete("/{user_id}/collection/{music_item_id}", status_code=204)
def remove_from_collection(user_id: int, music_item_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if user.id != user_id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Cannot modify another user's collection")
    entry = db.query(models.UserCollection).filter_by(user_id=user_id, music_item_id=music_item_id).one_or_none()
    if not entry:
        return
    db.delete(entry)
    db.commit()
    return