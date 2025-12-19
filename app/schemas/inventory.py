from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.inventory import MovementTypeEnum


class InventoryMovementBase(BaseModel):
    ingredient_id: int
    type: MovementTypeEnum
    quantity: Decimal
    unit_cost_at_time: Decimal | None = None
    note: str | None = None


class InventoryMovementCreate(InventoryMovementBase):
    pass


class InventoryMovementResponse(InventoryMovementBase):
    id: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryBalanceResponse(BaseModel):
    ingredient_id: int
    ingredient_name: str
    balance: Decimal
    unit: str
    avg_cost: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)
