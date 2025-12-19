from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict

from app.models.batch import BatchStatusEnum


class BatchConsumptionSchema(BaseModel):
    ingredient_id: int
    quantity_used: Decimal
    unit_cost_at_time: Decimal
    ingredient_name: str | None = None # Helpful for frontend

    model_config = ConfigDict(from_attributes=True)


class BatchCreate(BaseModel):
    recipe_id: int
    planned_units: Decimal


class BatchProduce(BaseModel):
    actual_units: Decimal | None = None


class BatchResponse(BaseModel):
    id: int
    code: str
    recipe_id: int
    recipe_name: str | None = None # Requires mapping
    status: BatchStatusEnum
    planned_units: Decimal
    actual_units: Decimal | None = None
    cost_snapshot_total: Decimal | None = None
    cost_snapshot_per_unit: Decimal | None = None
    created_at: datetime
    consumptions: List[BatchConsumptionSchema] = []

    model_config = ConfigDict(from_attributes=True)
