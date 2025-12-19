from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    total_inventory_value: Decimal
    monthly_production_cost: Decimal
    total_products_produced: Decimal


class LowStockAlert(BaseModel):
    ingredient_id: int
    name: str
    current_balance: Decimal
    unit: str
    # threshold: Decimal # Optional
