from sqlalchemy import Column, Integer, String, Boolean

from core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)

    password_hash = Column(String(255), nullable=False)

    role = Column(String(30), nullable=False, default="USER")

    is_active = Column(Boolean, nullable=False, default=True)