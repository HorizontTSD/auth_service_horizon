from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base_model import BaseModel


class Organization(BaseModel):
    __tablename__ = 'organizations'

    name: Mapped[str] = mapped_column(String)
    created_at = Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    email = Mapped[str] = mapped_column(String)
    owner_id = Mapped[int] = mapped_column(ForeignKey('user.id'))

    users: Mapped['User'] = relationship('User', back_populates='organization')