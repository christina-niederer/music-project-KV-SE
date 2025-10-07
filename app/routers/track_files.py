from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Response
from sqlalchemy.orm import Session
import io
from pydub import AudioSegment
from app.database import get_db
from app import models, schemas
from app.core.auth import require_admin, get_current_user

router = APIRouter()

@router.post("/tracks/{track_id}/file", response_model=schemas.TrackFileOut, dependencies=[Depends(require_admin)])
async def upload_track_file(track_id: int, upload: UploadFile = File(...), db: Session = Depends(get_db)):
    # Validate track exists and is TRACK
    track = db.get(models.MusicItem, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    if track.item_type != "TRACK":
        raise HTTPException(status_code=400, detail="Files can only be attached to TRACK items")

    data = await upload.read()
    original_size = len(data)

    # Protect server from very large uploads (avoid OOM / DB crash)
    MAX_UPLOAD_BYTES = 20_000_000  # ~20 MB
    if original_size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Uploaded file too large ({original_size} bytes). Max is {MAX_UPLOAD_BYTES} bytes.")

    # Re-encode the uploaded audio to a compact MP3 to save DB space and speed up downloads.
    try:
        in_buf = io.BytesIO(data)
        # Let pydub detect format from file bytes; explicitly use 'mp3' if necessary
        audio = AudioSegment.from_file(in_buf, format="mp3")
        out_buf = io.BytesIO()
        # Export as low-bitrate MP3 (64k). Adjust bitrate if you want different quality.
        audio.export(out_buf, format="mp3", bitrate="64k")
        out_bytes = out_buf.getvalue()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to transcode audio: {exc}")

    # Upsert TrackFile (one file per track) - store re-encoded bytes
    stored_bytes = out_bytes
    stored_size = len(stored_bytes)
    existing = db.query(models.TrackFile).filter(models.TrackFile.track_id == track_id).one_or_none()
    if existing:
        existing.filename = upload.filename
        existing.content_type = upload.content_type
        existing.file_data = stored_bytes
        existing.compressed = False
        existing.original_size = original_size
        db.commit()
        db.refresh(existing)
        return existing

    tf = models.TrackFile(track_id=track_id, filename=upload.filename, content_type=upload.content_type,
                           file_data=stored_bytes, compressed=False, original_size=original_size)
    db.add(tf)
    db.commit()
    db.refresh(tf)
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
 