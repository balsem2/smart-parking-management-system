from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
import secrets

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    security,
    verify_access_token,
    verify_password,
)
from app.models.reservation import Reservation
from app.models.user import User
from app.services.monitoring import create_alert, log_event
from app.services.email import send_password_reset_email

router = APIRouter(tags=["users"])
ROLES = {"SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY", "USER"}
STATUSES = {"PENDING", "ACTIVE", "REJECTED", "SUSPENDED"}
STAFF_ROLES = {"SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY"}


def create_user_record(data: dict, db: Session, creator_role: str = None):
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    role = data.get("role", "USER").upper()
    status = data.get("status")
    if status is None:
        if role == "USER":
            status = "ACTIVE"
        elif creator_role == "SUPER_ADMIN":
            status = "ACTIVE"
        else:
            status = "PENDING"
    status = status.upper()
    
    is_staff = role in STAFF_ROLES
    validate(username, email, password, role, status, is_staff=is_staff)
    ensure_unique(db, username, email)
    
    password_reset_token = None
    password_hash = None
    
    if password:
        password_hash = hash_password(password)
    elif is_staff:
        password_reset_token = secrets.token_urlsafe(32)
    
    result = User(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        status=status,
        is_active=data.get("is_active", status == "ACTIVE"),
        password_reset_token=password_reset_token,
    )
    db.add(result); db.commit(); db.refresh(result)
    response = {"message":"User created successfully", "id":result.id, "username":result.username, "email":result.email, "role":result.role, "status":result.status, "is_active":result.is_active}
    if password_reset_token:
        frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")
        reset_link = f"{frontend_url}/reset-password?token={password_reset_token}"
        email_sent = send_password_reset_email(result.email, result.username, reset_link)
        response["email_sent"] = email_sent
        response["email_status"] = (
            "sent" if email_sent else
            "smtp_not_configured" if not os.getenv("SMTP_HOST") else
            "send_failed"
        )
    return response


def validate(username: str, email: str, password: str | None, role: str, status: str | None = None, optional_password: bool = False, is_staff: bool = False) -> None:
    if not username or len(username) < 3: raise HTTPException(status_code=422, detail="username must contain at least 3 characters")
    if "@" not in email or email.startswith("@") or email.endswith("@"): raise HTTPException(status_code=422, detail="email must be valid")
    if is_staff:
        if password and len(password) < 8: raise HTTPException(status_code=422, detail="password must contain at least 8 characters")
    else:
        if (not optional_password or password) and (not password or len(password) < 8): raise HTTPException(status_code=422, detail="password must contain at least 8 characters")
    if role not in ROLES: raise HTTPException(status_code=422, detail="Invalid user role")
    if status is not None and status not in STATUSES: raise HTTPException(status_code=422, detail="Invalid user status")


def ensure_unique(db: Session, username: str, email: str, excluded_id: int | None = None) -> None:
    query = db.query(User).filter((User.username == username) | (User.email == email))
    if excluded_id is not None: query = query.filter(User.id != excluded_id)
    if query.first(): raise HTTPException(status_code=409, detail="Username or email is already in use")


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    payload = verify_access_token(credentials)
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user or not user.is_active or user.status != "ACTIVE": raise HTTPException(status_code=401, detail="Invalid token")
    return user


def require_roles(*allowed_roles):
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        return current_user

    return dependency


@router.post("/users")
def create_user(data: dict, db: Session = Depends(get_db), current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    return create_user_record(data, db, creator_role=current_user.role)


@router.get("/users")
def get_users(db: Session = Depends(get_db), current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    return db.query(User).all()


@router.get("/users/pending")
def get_pending_users(db: Session = Depends(get_db), current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    return db.query(User).filter(User.status == "PENDING").all()


@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users/{user_id}/approve")
def approve_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    user = get_user(user_id, db)
    if user.status not in {"PENDING", "REJECTED", "SUSPENDED"}:
        raise HTTPException(status_code=400, detail="User is not in a reviewable state")
    user.status = "ACTIVE"
    user.is_active = True
    db.commit(); db.refresh(user)
    return {"message": "User approved successfully", "user": user}


@router.post("/users/{user_id}/reject")
def reject_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    user = get_user(user_id, db)
    user.status = "REJECTED"
    user.is_active = False
    db.commit(); db.refresh(user)
    return {"message": "User rejected successfully", "user": user}


@router.put("/users/{user_id}")
def update_user(user_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    user = get_user(user_id, db)
    username, email, role, status, password = data.get("username", user.username).strip(), data.get("email", user.email).strip().lower(), data.get("role", user.role).upper(), data.get("status", user.status).upper(), data.get("password")
    validate(username, email, password, role, status, True)
    ensure_unique(db, username, email, user.id)
    user.username, user.email, user.role, user.status = username, email, role, status
    user.is_active = data.get("is_active", status == "ACTIVE")
    if password: user.password_hash = hash_password(password)
    db.commit(); db.refresh(user); return user


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    user = get_user(user_id, db)
    if db.query(Reservation).filter(Reservation.user_id == user.id).first(): raise HTTPException(status_code=409, detail="User has reservations and cannot be deleted; deactivate the user instead")
    db.delete(user); db.commit(); return {"message": "User deleted successfully"}


@router.post("/reset-password")
def reset_password(data: dict, db: Session = Depends(get_db)):
    token = data.get("token", "").strip()
    password = data.get("password", "").strip()
    
    if not token: raise HTTPException(status_code=422, detail="Reset token is required")
    if not password or len(password) < 8: raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    
    user = db.query(User).filter(User.password_reset_token == token).first()
    if not user: raise HTTPException(status_code=401, detail="Invalid or expired reset token")
    
    user.password_hash = hash_password(password)
    user.password_reset_token = None
    db.commit(); db.refresh(user)
    return {"message": "Password set successfully", "user": {"id": user.id, "username": user.username, "email": user.email}}


@router.post("/register")
def register(data: dict, db: Session = Depends(get_db)):
    payload = dict(data)
    payload["role"] = "USER"
    payload["status"] = "ACTIVE"
    payload["is_active"] = True
    return create_user_record(payload, db, creator_role="USER")


@router.post("/auth/login")
@router.post("/login")
def login(credentials: dict, db: Session = Depends(get_db)):
    username_or_email = credentials.get("username", "").strip() or credentials.get("email", "").strip()
    user = db.query(User).filter((User.username == username_or_email) | (User.email == username_or_email.lower())).first()
    password = credentials.get("password", "")
    if not user or not user.is_active or user.status != "ACTIVE" or not user.password_hash or not verify_password(password, user.password_hash):
        log_event(db, "ACCESS_DENIED", "Invalid login attempt", user_id=user.id if user else None)
        create_alert(db, "UNAUTHORIZED_ACCESS", "Invalid login attempt detected")
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message":"Login successful", "access_token":create_access_token({"user_id":user.id,"username":user.username,"role":user.role}), "token_type":"bearer"}


@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)): return {"id":current_user.id,"username":current_user.username,"email":current_user.email,"role":current_user.role,"status":current_user.status,"is_active":current_user.is_active}
