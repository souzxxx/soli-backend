from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import User
from app.models.ingredient import Ingredient


class MovementTypeEnum(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    type: Mapped[MovementTypeEnum] = mapped_column(Enum(MovementTypeEnum), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    unit_cost_at_time: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    ingredient: Mapped[Ingredient] = relationship("Ingredient")
    user: Mapped[User] = relationship("User")

    __table_args__ = (
        Index("idx_inventory_ingredient_created", "ingredient_id", "created_at"),
    )
