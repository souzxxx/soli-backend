from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.batch import Batch, BatchStatusEnum
from app.models.ingredient import Ingredient
from app.models.inventory import InventoryMovement, MovementTypeEnum
from app.schemas.dashboard import DashboardStatsResponse, LowStockAlert


class DashboardService:
    def get_stats(self, db: Session) -> DashboardStatsResponse:
        # 1. Total Inventory Value
        # Efficient strategy: Get all balances via one query if possible, or iterate
        # SQL: SELECT ingredient_id, SUM(CASE WHEN type='OUT' THEN -quantity ELSE quantity END) FROM inventory_movements GROUP BY ingredient_id
        
        balance_query = (
            db.query(
                InventoryMovement.ingredient_id,
                func.sum(
                    case(
                        (InventoryMovement.type == MovementTypeEnum.OUT, -InventoryMovement.quantity),
                        else_=InventoryMovement.quantity
                    )
                ).label("balance")
            )
            .group_by(InventoryMovement.ingredient_id)
            .all()
        )
        
        # Map ingredient costs
        ingredients = db.query(Ingredient).all()
        cost_map = {i.id: i.cost_per_unit for i in ingredients}
        
        total_value = Decimal(0)
        for row in balance_query:
            ing_id = row.ingredient_id
            balance = row.balance or 0
            if balance > 0:
                cost = cost_map.get(ing_id, 0)
                total_value += balance * Decimal(cost)
        
        # 2. Monthly Production Cost & Quantity
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)
        
        production_stats = (
            db.query(
                func.sum(Batch.cost_snapshot_total).label("total_cost"),
                func.sum(Batch.actual_units).label("total_units")
            )
            .filter(
                Batch.status == BatchStatusEnum.PRODUCED,
                Batch.created_at >= start_of_month
            )
            .first()
        )
        
        monthly_cost = production_stats.total_cost or Decimal(0)
        monthly_units = production_stats.total_units or Decimal(0)
        
        return DashboardStatsResponse(
            total_inventory_value=total_value,
            monthly_production_cost=monthly_cost,
            total_products_produced=monthly_units
        )

    def get_low_stock_alerts(self, db: Session, threshold: float = 10.0) -> list[LowStockAlert]:
        # This reuses the balance query logic
        # For simplicity, let's reuse the same aggregation query
        balance_query = (
            db.query(
                InventoryMovement.ingredient_id,
                func.sum(
                    case(
                        (InventoryMovement.type == MovementTypeEnum.OUT, -InventoryMovement.quantity),
                        else_=InventoryMovement.quantity
                    )
                ).label("balance")
            )
            .group_by(InventoryMovement.ingredient_id)
            .all()
        )
        
        alerts = []
        ingredients = {i.id: i for i in db.query(Ingredient).all()}
        
        for row in balance_query:
            balance = row.balance or 0
            if balance < threshold:
                ing = ingredients.get(row.ingredient_id)
                if ing and ing.active: # Only active ingredients
                    alerts.append(
                        LowStockAlert(
                            ingredient_id=ing.id,
                            name=ing.name,
                            current_balance=balance,
                            unit=ing.unit
                        )
                    )
        # Note: Ingredients with NO movements are not in balance_query.
        # Should we alert on them? Maybe. They have balance 0.
        # Let's check ingredients that are NOT in the query result.
        
        moved_ids = set(row.ingredient_id for row in balance_query)
        for ing_id, ing in ingredients.items():
            if ing_id not in moved_ids and ing.active:
                if 0 < threshold:
                     alerts.append(
                        LowStockAlert(
                            ingredient_id=ing.id,
                            name=ing.name,
                            current_balance=Decimal(0),
                            unit=ing.unit
                        )
                    )
        
        return alerts

dashboard_service = DashboardService()
