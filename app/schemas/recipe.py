from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict

from app.models.ingredient import UnitEnum


# --- Recipe Item Schemas ---
class RecipeItemCreate(BaseModel):
    ingredient_id: int
    quantity: Decimal
    waste_factor: Decimal = Decimal(0)


class RecipeItemResponse(BaseModel):
    id: int
    ingredient_id: int
    quantity: Decimal
    waste_factor: Decimal
    
    # We might want to show ingredient name here for convenience
    # For now, keep it simple mapping to DB model

    model_config = ConfigDict(from_attributes=True)


# --- Recipe Schemas ---
class RecipeBase(BaseModel):
    name: str
    yield_quantity: Decimal
    yield_unit: UnitEnum
    notes: str | None = None


class RecipeCreate(RecipeBase):
    items: List[RecipeItemCreate]


class RecipeUpdate(BaseModel):
    name: str | None = None
    yield_quantity: Decimal | None = None
    yield_unit: UnitEnum | None = None
    notes: str | None = None


class RecipeResponse(RecipeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[RecipeItemResponse]

    model_config = ConfigDict(from_attributes=True)


# --- Cost Response Schemas ---
class ItemCostBreakdown(BaseModel):
    ingredient_id: int
    ingredient_name: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal
    total_cost: Decimal # quantity * unit_cost


class RecipeCostResponse(BaseModel):
    recipe_id: int
    recipe_name: str
    total_cost: Decimal
    cost_per_unit: Decimal
    yield_quantity: Decimal
    breakdown: List[ItemCostBreakdown]
