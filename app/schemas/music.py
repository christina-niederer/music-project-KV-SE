from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List

from app.schemas.user import UserOut

# Artist
class ArtistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

class ArtistOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# Genre
class GenreCreate(BaseModel):
    name: str

class GenreOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# Music Item
class MusicItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    item_type: str = Field(pattern="^(TRACK|ALBUM|OTHER)$")
    release_year: Optional[int] = None
    duration_seconds: Optional[int] = None

class MusicItemCreate(MusicItemBase):
    artist_ids: Optional[list[int]] = None
    genre_ids: Optional[list[int]] = None
    track_ids: Optional[list[int]] = None  # Only valid when item_type == 'ALBUM'

class MusicItemUpdate(BaseModel):
    title: Optional[str] = None
    item_type: Optional[str] = Field(default=None, pattern="^(TRACK|ALBUM|OTHER)$")
    release_year: Optional[int] = None
    duration_seconds: Optional[int] = None
    artist_ids: Optional[list[int]] = None
    genre_ids: Optional[list[int]] = None
    track_ids: Optional[list[int]] = None  # replace full album track list if provided - Only valid when item_type == 'ALBUM'

class MusicItemOut(BaseModel):
    id: int
    title: str
    item_type: str
    release_year: Optional[int] = None
    duration_seconds: Optional[int] = None
    artists: list[ArtistOut] = []
    genres: list[GenreOut] = []
    tracks: list['MusicItemOut'] = []  # recursive for album contents (only set when item is ALBUM)
    class Config:
        from_attributes = True

# Review
class ReviewCreate(BaseModel):
    music_item_id: int
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    text: Optional[str] = Field(default=None, max_length=2000)

class ReviewOut(BaseModel):
    id: int
    user_id: int
    music_item_id: int
    rating: Optional[int] = None
    text: Optional[str] = None
    user: UserOut
    class Config:
         model_config = {"from_attributes": True}

# Collection
class CollectionUpsert(BaseModel):
    preference: Optional[str] = Field(default=None, pattern="^(LIKE|DISLIKE|NONE)$")
    is_favourite: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=2000)

class CollectionEntryOut(BaseModel):
    user_id: int
    music_item_id: int
    preference: str
    is_favourite: bool
    note: Optional[str] = None
    music_item: Optional[MusicItemOut] = None  # enriched when returning collections
    class Config:
        model_config = {"from_attributes": True}

# Track file (binary stored compressed in DB)
class TrackFileOut(BaseModel):
    id: int
    track_id: int
    filename: str
    content_type: Optional[str] = None
    compressed: bool
    original_size: Optional[int] = None
    class Config:
        from_attributes = True

# Forward reference resolution for recursive model
MusicItemOut.model_rebuild()