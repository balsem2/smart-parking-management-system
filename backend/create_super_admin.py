import os

import app.models  # noqa: F401
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


username = os.getenv("SUPER_ADMIN_USERNAME")
email = os.getenv("SUPER_ADMIN_EMAIL")
password = os.getenv("SUPER_ADMIN_PASSWORD")

if not username or not email or not password:
    raise RuntimeError(
        "SUPER_ADMIN_USERNAME, SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD must be configured"
    )

db = SessionLocal()
try:
    existing = db.query(User).filter(
        (User.username == username) | (User.email == email.lower())
    ).first()

    if existing:
        print(f"EXISTS:{existing.username}:{existing.email}:{existing.role}:{existing.status}")
    else:
        user = User(
            username=username,
            email=email.lower(),
            password_hash=hash_password(password),
            role='SUPER_ADMIN',
            status='ACTIVE',
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"CREATED:{user.id}:{user.username}:{user.email}:{user.role}:{user.status}")
finally:
    db.close()
