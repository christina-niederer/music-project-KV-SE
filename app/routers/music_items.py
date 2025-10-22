from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app import models, schemas
from app.core.auth import require_admin
from sqlalchemy import func


router = APIRouter()

def calculate_album_duration(db: Session, album_id: int) -> int:
    """Calculate total duration of an album by summing its tracks' durations."""
    result = db.query(func.sum(models.MusicItem.duration_seconds)).join(
    models.album_tracks,
    models.album_tracks.c.track_id == models.MusicItem.id
).filter(models.album_tracks.c.album_id == album_id).scalar()
    return result or 0

def serialize_music_item(mi: models.MusicItem, include_tracks: bool = True) -> schemas.MusicItemOut:
    # Base serialization
    data = dict(
        id=mi.id,
        title=mi.title,
        item_type=mi.item_type,
        release_year=mi.release_year,
        duration_seconds=mi.duration_seconds,
        artists=[schemas.ArtistOut.model_validate(a.artist) for a in mi.artists],
        genres=[schemas.GenreOut.model_validate(g.genre) for g in mi.genres],
    )
    # Add tracks if album
    if include_tracks and mi.item_type == "ALBUM":
        # Ensure album_tracks loaded
        tracks = []
        for at in sorted(mi.album_tracks, key=lambda x: x.track_number):
            # Avoid deep recursion by not including tracks' own album memberships
            tracks.append(serialize_music_item(at.track, include_tracks=False))
        data["tracks"] = tracks
    else:
        data["tracks"] = []
    return schemas.MusicItemOut(**data)

@router.post("", response_model=schemas.MusicItemOut, status_code=201, dependencies=[Depends(require_admin)])
def create_music_item(payload: schemas.MusicItemCreate, db: Session = Depends(get_db)):
    # Validate duration_seconds not provided for albums
    if payload.item_type == "ALBUM" and payload.duration_seconds is not None:
        raise HTTPException(status_code=400, detail="duration_seconds cannot be set for albums; it is calculated automatically")
    mi = models.MusicItem(
        title=payload.title,
        item_type=payload.item_type,
        release_year=payload.release_year,
        duration_seconds=payload.duration_seconds if payload.item_type != "ALBUM" else 0,  # Start with 0 for albums
    )
    db.add(mi)
    db.flush()  # get id

    if payload.artist_ids:
        for aid in payload.artist_ids:
            db.add(models.MusicItemArtist(music_item_id=mi.id, artist_id=aid, role="PRIMARY"))
    if payload.genre_ids:
        for gid in payload.genre_ids:
            db.add(models.MusicItemGenre(music_item_id=mi.id, genre_id=gid))

    # Album tracks (only if album)
    if payload.item_type == "ALBUM" and payload.track_ids:
        # Validate tracks exist and are TRACK type
        tracks = db.query(models.MusicItem).filter(models.MusicItem.id.in_(payload.track_ids)).all()
        found_ids = {t.id for t in tracks}
        missing = set(payload.track_ids) - found_ids
        if missing:
            raise HTTPException(status_code=400, detail=f"Tracks not found: {sorted(missing)}")
        # Ensure all are TRACK type (prevent albums in albums)
        invalid_types = [t.id for t in tracks if t.item_type != "TRACK"]
        if invalid_types:
            raise HTTPException(status_code=400, detail=f"Only TRACK items can be added to albums: {sorted(invalid_types)}")
        for idx, tid in enumerate(payload.track_ids, start=1):
            db.add(models.AlbumTrack(album_id=mi.id, track_id=tid, track_number=idx))

    # Calculate duration for albums
    if mi.item_type == "ALBUM":
    # Album duration calculation skipped (no album_tracks table defined)
        mi.duration_seconds = 0


    db.commit()
    db.refresh(mi)
    return get_music_item(mi.id, db)

@router.get("", response_model=list[schemas.MusicItemOut])
def list_music_items(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="Search in title"),
    genre_id: int | None = None,
    artist_id: int | None = None,
):
    query = db.query(models.MusicItem).options(
        selectinload(models.MusicItem.artists).selectinload(models.MusicItemArtist.artist),
        selectinload(models.MusicItem.genres).selectinload(models.MusicItemGenre.genre),
    )
    if q:
        query = query.filter(models.MusicItem.title.ilike(f"%{q}%"))
    if genre_id:
        query = query.join(models.MusicItem.genres).filter(models.MusicItemGenre.genre_id == genre_id)
    if artist_id:
        query = query.join(models.MusicItem.artists).filter(models.MusicItemArtist.artist_id == artist_id)
    items = query.all()
    return [serialize_music_item(mi) for mi in items]

@router.get("/{item_id}", response_model=schemas.MusicItemOut)
def get_music_item(item_id: int, db: Session = Depends(get_db)):
    mi = db.query(models.MusicItem).options(
        selectinload(models.MusicItem.artists).selectinload(models.MusicItemArtist.artist),
        selectinload(models.MusicItem.genres).selectinload(models.MusicItemGenre.genre),
        selectinload(models.MusicItem.album_tracks).selectinload(models.AlbumTrack.track).selectinload(models.MusicItem.artists).selectinload(models.MusicItemArtist.artist),
        selectinload(models.MusicItem.album_tracks).selectinload(models.AlbumTrack.track).selectinload(models.MusicItem.genres).selectinload(models.MusicItemGenre.genre),
    ).get(item_id)
    if not mi:
        raise HTTPException(status_code=404, detail="Music item not found")
    return serialize_music_item(mi)

@router.put("/{item_id}", response_model=schemas.MusicItemOut, dependencies=[Depends(require_admin)])
def update_music_item(item_id: int, payload: schemas.MusicItemUpdate, db: Session = Depends(get_db)):
    mi = db.get(models.MusicItem, item_id)
    if not mi:
        raise HTTPException(status_code=404, detail="Music item not found")

    # Validate duration_seconds not provided for albums
    if payload.duration_seconds is not None and mi.item_type == "ALBUM":
        raise HTTPException(status_code=400, detail="duration_seconds cannot be updated for albums; it is calculated automatically")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in {"artist_ids", "genre_ids", "track_ids", "item_type"}: #Item Type cannot be changed
            continue
        setattr(mi, field, value)

    if payload.artist_ids is not None:
        db.query(models.MusicItemArtist).filter(models.MusicItemArtist.music_item_id == item_id).delete()
        for aid in payload.artist_ids:
            db.add(models.MusicItemArtist(music_item_id=item_id, artist_id=aid, role="PRIMARY"))
    if payload.genre_ids is not None:
        db.query(models.MusicItemGenre).filter(models.MusicItemGenre.music_item_id == item_id).delete()
        for gid in payload.genre_ids:
            db.add(models.MusicItemGenre(music_item_id=item_id, genre_id=gid))
    if payload.track_ids is not None:
        # Replace album track list (only allowed if item is album)
        if mi.item_type != "ALBUM":
            raise HTTPException(status_code=400, detail="Can only set track_ids for album items")
        db.query(models.AlbumTrack).filter(models.AlbumTrack.album_id == item_id).delete()
        if payload.track_ids:
            tracks = db.query(models.MusicItem).filter(models.MusicItem.id.in_(payload.track_ids)).all()
            found_ids = {t.id for t in tracks}
            missing = set(payload.track_ids) - found_ids
            if missing:
                raise HTTPException(status_code=400, detail=f"Tracks not found: {sorted(missing)}")
            # Ensure all are TRACK type (prevent albums in albums)
            invalid_types = [t.id for t in tracks if t.item_type != "TRACK"]
            if invalid_types:
                raise HTTPException(status_code=400, detail=f"Only TRACK items can be added to albums: {sorted(invalid_types)}")
            for idx, tid in enumerate(payload.track_ids, start=1):
                db.add(models.AlbumTrack(album_id=item_id, track_id=tid, track_number=idx))

    db.commit()
    db.refresh(mi)
    return get_music_item(item_id, db)

@router.delete("/{item_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_music_item(item_id: int, db: Session = Depends(get_db)):
    mi = db.get(models.MusicItem, item_id)
    if not mi:
        return
    db.delete(mi)
    db.commit()
    return