from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Response, BackgroundTasks
from sqlalchemy.orm import Session
import io
from pydub import AudioSegment
from app.database import get_db, SessionLocal
from app import models, schemas
from app.core.auth import require_admin, get_current_user
import time

router = APIRouter()

@router.post("/tracks/{track_id}/file", response_model=schemas.TrackFileOut, dependencies=[Depends(require_admin)])
async def upload_track_file(track_id: int, background: BackgroundTasks, upload: UploadFile = File(...), db: Session = Depends(get_db)):
    start_time = time.perf_counter()
    log = []

    def log_time(msg):
        elapsed = int((time.perf_counter() - start_time) * 1000)
        log.append(f"{elapsed}ms: {msg}")

    log_time("Start upload_track_file")

    # Validate track exists and is TRACK
    track = db.get(models.MusicItem, track_id)
    log_time("Checked track existence")
    if not track:
        log_time("Track not found")
        print("\n".join(log))
        raise HTTPException(status_code=404, detail="Track not found")
    if track.item_type != "TRACK":
        log_time("Item is not TRACK")
        print("\n".join(log))
        raise HTTPException(status_code=400, detail="Files can only be attached to TRACK items")

    data = await upload.read()
    log_time("Read upload data")
    original_size = len(data)

    # Protect server from very large uploads (avoid OOM / DB crash)
    MAX_UPLOAD_BYTES = 20_000_000  # ~20 MB
    if original_size > MAX_UPLOAD_BYTES:
        log_time("File too large")
        print("\n".join(log))
        raise HTTPException(status_code=413, detail=f"Uploaded file too large ({original_size} bytes). Max is {MAX_UPLOAD_BYTES} bytes.")

    # Instead of transcode synchronously, create a placeholder DB record and do heavy work in background
    existing = db.query(models.TrackFile).filter(models.TrackFile.track_id == track_id).one_or_none()
    log_time("Checked for existing TrackFile")
    if existing:
        # overwrite metadata but clear data until background task finishes
        existing.filename = upload.filename
        existing.content_type = upload.content_type
        existing.file_data = b""
        existing.compressed = False
        existing.original_size = original_size
        db.commit()
        db.refresh(existing)
        tf = existing
        log_time("Updated existing TrackFile")
    else:
        tf = models.TrackFile(track_id=track_id, filename=upload.filename, content_type=upload.content_type,
                               file_data=b"", compressed=False, original_size=original_size)
        db.add(tf)
        db.commit()
        db.refresh(tf)
        log_time("Created new TrackFile")

    # Background worker will transcode and store the real bytes
    def transcode_and_store(trackfile_id: int, raw_bytes: bytes, filename: str, content_type: str):
        session = SessionLocal()
        bg_start = time.perf_counter()
        def bg_log(msg):
            elapsed = int((time.perf_counter() - bg_start) * 1000)
            print(f"[BG] {elapsed}ms: {msg}")
        bg_log("Start transcode_and_store")
        try:
            tf_obj = session.get(models.TrackFile, trackfile_id)
            bg_log("Fetched TrackFile from DB")
            if not tf_obj:
                bg_log("TrackFile not found")
                session.close()
                return
            try:
                in_buf = io.BytesIO(raw_bytes)
                audio = AudioSegment.from_file(in_buf, format="mp3")
                bg_log("Loaded audio with pydub")
                out_buf = io.BytesIO()
                audio.export(out_buf, format="mp3", bitrate="64k")
                out_bytes = out_buf.getvalue()
                bg_log("Exported audio to mp3 64k")
            except Exception:
                # On transcode failure, leave placeholder and record original_size; do not raise
                bg_log("Transcode failed")
                session.close()
                return
            tf_obj.file_data = out_bytes
            tf_obj.compressed = False
            tf_obj.original_size = len(raw_bytes)
            session.add(tf_obj)
            session.commit()
            bg_log("Saved transcoded file to DB")
        finally:
            session.close()
            bg_log("Closed DB session")

    # Schedule background transcoding
    background.add_task(transcode_and_store, tf.id, data, upload.filename, upload.content_type)
    log_time("Scheduled background task")
    print("\n".join(log))
    # Return placeholder record (consumer can poll or re-GET to retrieve once processed)
    return tf

@router.get("/tracks/{track_id}/file")
def download_track_file(track_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    tf = db.query(models.TrackFile).filter(models.TrackFile.track_id == track_id).one_or_none()
    if not tf:
        raise HTTPException(status_code=404, detail="File not found")
    data = tf.file_data
    # No decompression step needed — files are stored as ready-to-serve MP3
    headers = {"Content-Disposition": f"attachment; filename=\"{tf.filename}\""}
    return Response(content=data, media_type=tf.content_type or "audio/mpeg", headers=headers)
 