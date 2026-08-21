from sqlalchemy import Boolean, Column, Integer, String

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    full_name = Column(String(100), nullable=True)
    national_id = Column(String(30), nullable=True, unique=True, index=True)

    password_hash = Column(String(255), nullable=True)

    role = Column(String(30), nullable=False, default="USER")
    status = Column(String(30), nullable=False, default="ACTIVE")

    is_active = Column(Boolean, nullable=False, default=True)
    password_reset_token = Column(String(255), nullable=True)
