import app.models  # noqa: F401
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


db = SessionLocal()
try:
    existing = db.query(User).filter(
        (User.username == 'Balsem') | (User.email == 'zouabibalsem1@gmail.com')
    ).first()

    if existing:
        print(f"EXISTS:{existing.username}:{existing.email}:{existing.role}:{existing.status}")
    else:
        user = User(
            username='Balsem',
            email='zouabibalsem1@gmail.com',
            password_hash=hash_password('Balsemzouabi2026'),
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
