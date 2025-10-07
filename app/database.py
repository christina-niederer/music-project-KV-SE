from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

engine = create_engine(settings.database_url, echo=settings.echo_sql, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import models so metadata is populated
    from app.models.user import User
    from app.models.music import Artist, Genre, MusicItem, MusicItemArtist, MusicItemGenre, Review, UserCollection, AlbumTrack
