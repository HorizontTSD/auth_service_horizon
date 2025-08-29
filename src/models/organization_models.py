from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base_model import BaseModel
from db_clients.config import db_settings


class Organization(BaseModel):
    __tablename__ = db_settings.tables.ORGANIZATIONS

    name: Mapped[str] = mapped_column(String)
    email = Mapped[str] = mapped_column(String)
    owner_id = Mapped[int] = mapped_column(ForeignKey('user.id'))

    users: Mapped['User'] = relationship('User', back_populates='organization')