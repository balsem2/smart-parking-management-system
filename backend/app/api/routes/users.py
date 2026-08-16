from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import create_access_token, hash_password, security, verify_access_token, verify_password
from models.reservation import Reservation
from models.user import User
from services.monitoring import create_alert, log_event

router = APIRouter(tags=["users"])
ROLES = {"SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY", "USER"}


def validate(username: str, email: str, password: str | None, role: str, optional_password: bool = False) -> None:
    if not username or len(username) < 3: raise HTTPException(status_code=422, detail="username must contain at least 3 characters")
    if "@" not in email or email.startswith("@") or email.endswith("@"): raise HTTPException(status_code=422, detail="email must be valid")
    if (not optional_password or password) and (not password or len(password) < 8): raise HTTPException(status_code=422, detail="password must contain at least 8 characters")
    if role not in ROLES: raise HTTPException(status_code=422, detail="Invalid user role")


def ensure_unique(db: Session, username: str, email: str, excluded_id: int | None = None) -> None:
    query = db.query(User).filter((User.username == username) | (User.email == email))
    if excluded_id is not None: query = query.filter(User.id != excluded_id)
    if query.first(): raise HTTPException(status_code=409, detail="Username or email is already in use")


def create_user_record(data: dict, db: Session):
    username, email, password, role = data.get("username", "").strip(), data.get("email", "").strip().lower(), data.get("password", ""), data.get("role", "USER").upper()
    validate(username, email, password, role); ensure_unique(db, username, email)
    result = User(username=username, email=email, password_hash=hash_password(password), role=role, is_active=data.get("is_active", True)); db.add(result); db.commit(); db.refresh(result)
    return {"message":"User created successfully", "id":result.id, "username":result.username, "email":result.email, "role":result.role, "is_active":result.is_active}


@router.post("/users")
def create_user(data: dict, db: Session = Depends(get_db)): return create_user_record(data, db)
@router.get("/users")
def get_users(db: Session = Depends(get_db)): return db.query(User).all()
@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    return user
@router.put("/users/{user_id}")
def update_user(user_id: int, data: dict, db: Session = Depends(get_db)):
    user = get_user(user_id, db); username, email, role, password = data.get("username", user.username).strip(), data.get("email", user.email).strip().lower(), data.get("role", user.role).upper(), data.get("password")
    validate(username, email, password, role, True); ensure_unique(db, username, email, user.id); user.username, user.email, user.role = username, email, role
    if password: user.password_hash = hash_password(password)
    if "is_active" in data:
        if not isinstance(data["is_active"], bool): raise HTTPException(status_code=422, detail="is_active must be a boolean")
        user.is_active = data["is_active"]
    db.commit(); db.refresh(user); return user
@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user(user_id, db)
    if db.query(Reservation).filter(Reservation.user_id == user.id).first(): raise HTTPException(status_code=409, detail="User has reservations and cannot be deleted; deactivate the user instead")
    db.delete(user); db.commit(); return {"message": "User deleted successfully"}
@router.post("/register")
def register(data: dict, db: Session = Depends(get_db)):
    data["role"] = "USER"; return create_user_record(data, db)
@router.post("/auth/login")
@router.post("/login")
def login(credentials: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.get("username", "").strip()).first(); password = credentials.get("password", "")
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        log_event(db, "ACCESS_DENIED", "Invalid login attempt", user_id=user.id if user else None); create_alert(db, "UNAUTHORIZED_ACCESS", "Invalid login attempt detected"); db.commit(); raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message":"Login successful", "access_token":create_access_token({"user_id":user.id,"username":user.username,"role":user.role}), "token_type":"bearer"}
def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    payload = verify_access_token(credentials); user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user or not user.is_active: raise HTTPException(status_code=401, detail="Invalid token")
    return user
@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)): return {"id":current_user.id,"username":current_user.username,"email":current_user.email,"role":current_user.role,"is_active":current_user.is_active}
