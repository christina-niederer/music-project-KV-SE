from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Boolean, Text, Integer, LargeBinary, DateTime, func
from sqlalchemy import UniqueConstraint
from app.database import Base
from typing import Optional

class Artist(Base):
    __tablename__ = "artists"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)

    items = relationship("MusicItemArtist", back_populates="artist", cascade="all, delete-orphan")

class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    items = relationship("MusicItemGenre", back_populates="genre", cascade="all, delete-orphan")

class MusicItem(Base):
    __tablename__ = "music_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(250), index=True)
    item_type: Mapped[str] = mapped_column(String(16), default="TRACK")  # TRACK | ALBUM | OTHER
    release_year: Mapped[Optional[int]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(nullable=True)

    artists = relationship("MusicItemArtist", back_populates="music_item", cascade="all, delete-orphan")
    genres = relationship("MusicItemGenre", back_populates="music_item", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="music_item", cascade="all, delete-orphan")
    collectors = relationship("UserCollection", back_populates="music_item", cascade="all, delete-orphan")
    # Album <-> Track relationship (self-referential through AlbumTrack)
    album_tracks = relationship("AlbumTrack", back_populates="album", cascade="all, delete-orphan", foreign_keys="AlbumTrack.album_id", order_by="AlbumTrack.track_number")
    track_albums = relationship("AlbumTrack", back_populates="track", cascade="all, delete-orphan", foreign_keys="AlbumTrack.track_id")
    # Optional binary file attached to a track
    track_file = relationship("TrackFile", back_populates="track", uselist=False, cascade="all, delete-orphan")

class MusicItemArtist(Base):
    __tablename__ = "music_item_artists"
    music_item_id: Mapped[int] = mapped_column(ForeignKey("music_items.id"), primary_key=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="PRIMARY", primary_key=True) # PRIMARY | FEATURED | PRODUCER ...

    music_item = relationship("MusicItem", back_populates="artists")
    artist = relationship("Artist", back_populates="items")

class MusicItemGenre(Base):
    __tablename__ = "music_item_genres"
    music_item_id: Mapped[int] = mapped_column(ForeignKey("music_items.id"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id"), primary_key=True)

    music_item = relationship("MusicItem", back_populates="genres")
    genre = relationship("Genre", back_populates="items")

class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    music_item_id: Mapped[int] = mapped_column(ForeignKey("music_items.id"), index=True)
    rating: Mapped[Optional[int]] = mapped_column(nullable=True)  # 1..5
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="reviews")
    music_item = relationship("MusicItem", back_populates="reviews")

    __table_args__ = (UniqueConstraint("user_id", "music_item_id", name="uq_review_user_item"),)

class UserCollection(Base):
    __tablename__ = "user_collections"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    music_item_id: Mapped[int] = mapped_column(ForeignKey("music_items.id"), primary_key=True)
    preference: Mapped[str] = mapped_column(String(10), default="NONE")  # LIKE | DISLIKE | NONE
    is_favourite: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="collections")
    music_item = relationship("MusicItem", back_populates="collectors")

class AlbumTrack(Base):
    """Association table linking an album (MusicItem with item_type='ALBUM') to its tracks (MusicItem with item_type='TRACK').
    A track can appear in multiple albums. Only admins may manage this mapping.
    """
    __tablename__ = "album_tracks"
    album_id: Mapped[int] = mapped_column(ForeignKey("music_items.id"), primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("music_items.id"), primary_key=True)
    track_number: Mapped[int] = mapped_column(Integer, default=0)

    album = relationship("MusicItem", foreign_keys=[album_id], back_populates="album_tracks")
    track = relationship("MusicItem", foreign_keys=[track_id], back_populates="track_albums")


class TrackFile(Base):
    __tablename__ = "track_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("music_items.id"), unique=True, index=True)
    filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    file_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=False)
    compressed: Mapped[bool] = mapped_column(Boolean, default=True)
    original_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    track = relationship("MusicItem", back_populates="track_file", foreign_keys=[track_id])