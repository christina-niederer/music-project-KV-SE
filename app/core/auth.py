from fastapi import APIRouter, Depends, Header, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter()

# Very lightweight demo authentication. - Task 3 will fix that.
def get_current_user(
    db: Session = Depends(get_db),
    x_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
    x_role: Optional[str] = Header(default=None, alias="X-Role"),
) -> models.User:
    if x_user_id is None or x_role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Provide X-User-Id and X-Role headers.")
    user = db.get(models.User, x_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != x_role:
        raise HTTPException(status_code=403, detail="Role/header mismatch")
    return user

def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    user = models.User(email=payload.email, display_name=payload.display_name, role=payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()