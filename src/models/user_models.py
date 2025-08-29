from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base_model import BaseModel
from db_clients.config import db_settings


class User(BaseModel):
    __tablename__ = db_settings.tables.USERS
    
    organization_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    login: Mapped[str] = mapped_column(String)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    nickname: Mapped[str | None] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    password: Mapped[str] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    refresh_tokens: Mapped[list['RefreshToken']] = relationship('RefreshToken', back_populates='user')
    organization: Mapped['Organization'] = relationship('Organization', back_populates='users')


class RefreshToken(BaseModel):
    __tablename__ = db_settings.tables.REFRESH_TOKENS
    
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    token: Mapped[str] = mapped_column(String)
    jti: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped['User'] = relationship('User', back_populates='refresh_tokens')