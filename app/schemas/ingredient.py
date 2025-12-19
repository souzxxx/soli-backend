from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.ingredient import UnitEnum


class IngredientBase(BaseModel):
    name: str
    unit: UnitEnum
    cost_per_unit: Decimal
    supplier_name: str | None = None
    active: bool = True


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(BaseModel):
    name: str | None = None
    unit: UnitEnum | None = None
    cost_per_unit: Decimal | None = None
    supplier_name: str | None = None
    active: bool | None = None


class IngredientResponse(IngredientBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
