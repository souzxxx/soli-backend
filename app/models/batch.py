from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.models.user import User


class BatchStatusEnum(str, enum.Enum):
    PLANNED = "PLANNED"
    PRODUCED = "PRODUCED"
    CANCELED = "CANCELED"


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    
    status: Mapped[BatchStatusEnum] = mapped_column(
        Enum(BatchStatusEnum), default=BatchStatusEnum.PLANNED, nullable=False
    )
    
    planned_units: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    actual_units: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    
    # Cost Snapshots
    cost_snapshot_total: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    cost_snapshot_per_unit: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    recipe: Mapped[Recipe] = relationship("Recipe")
    user: Mapped[User] = relationship("User")
    consumptions: Mapped[list["BatchConsumption"]] = relationship(
        "BatchConsumption", back_populates="batch", cascade="all, delete-orphan"
    )


class BatchConsumption(Base):
    __tablename__ = "batch_consumptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    
    quantity_used: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    unit_cost_at_time: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    # Relationships
    batch: Mapped[Batch] = relationship("Batch", back_populates="consumptions")
    ingredient: Mapped[Ingredient] = relationship("Ingredient")

    __table_args__ = (
        UniqueConstraint("batch_id", "ingredient_id", name="uq_batch_consumption_ingredient"),
    )
