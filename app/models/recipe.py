from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.ingredient import Ingredient, UnitEnum
from app.models.user import User


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    yield_quantity: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=1.0)
    yield_unit: Mapped[UnitEnum] = mapped_column(Enum(UnitEnum), nullable=False, default=UnitEnum.un)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    items: Mapped[list["RecipeItem"]] = relationship("RecipeItem", back_populates="recipe", cascade="all, delete-orphan")


class RecipeItem(Base):
    __tablename__ = "recipe_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    waste_factor: Mapped[float] = mapped_column(Numeric(10, 4), default=0.0)

    # Relationships
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="items")
    ingredient: Mapped[Ingredient] = relationship("Ingredient")

    __table_args__ = (
        UniqueConstraint("recipe_id", "ingredient_id", name="uq_recipe_ingredient"),
    )
