from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import security, verify_access_token
from app.models.user import User


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> User:
    payload = verify_access_token(credentials)
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user or not user.is_active or user.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def require_roles(*allowed_roles):
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return dependency
