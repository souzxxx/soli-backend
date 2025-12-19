from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.batch import Batch, BatchConsumption, BatchStatusEnum
from app.models.inventory import MovementTypeEnum
from app.models.recipe import Recipe
from app.schemas.batch import BatchCreate, BatchProduce
from app.schemas.inventory import InventoryMovementCreate
from app.services.inventory_service import inventory_service


class BatchService:
    def create_batch(self, db: Session, batch_in: BatchCreate, user_id: int) -> Batch:
        # Generate Code (Simple implementation: SOL-{timestamp})
        code = f"SOL-{int(datetime.utcnow().timestamp())}"
        
        batch = Batch(
            code=code,
            recipe_id=batch_in.recipe_id,
            planned_units=batch_in.planned_units,
            status=BatchStatusEnum.PLANNED,
            created_by=user_id
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        return batch

    def produce_batch(
        self, db: Session, batch_id: int, produce_in: BatchProduce, user_id: int
    ) -> Batch:
        batch = db.query(Batch).options(joinedload(Batch.recipe)).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError("Batch not found")
        
        if batch.status != BatchStatusEnum.PLANNED:
            raise ValueError(f"Cannot produce batch with status {batch.status}")

        # Determine actual units
        actual_units = produce_in.actual_units if produce_in.actual_units is not None else batch.planned_units
        
        # Get Recipe Items to calculate consumption
        # Using joinedload above on batch.recipe is inconsistent, 
        # better to fetch recipe with items explicitly or rely on lazy load if session open.
        # Let's verify recipe structure.
        recipe = db.query(Recipe).options(joinedload(Recipe.items)).filter(Recipe.id == batch.recipe_id).first()
        
        if not recipe or not recipe.items:
             raise ValueError("Recipe not found or has no items")

        # Validation Pass: Check Stock
        stock_deductions = []
        total_cost = Decimal(0)

        # Factor = Actual Produced / Recipe Yield
        # Example: Recipe Yield 10. Produced 20. Factor = 2.
        # Avoid division by zero
        if recipe.yield_quantity <= 0:
             raise ValueError("Recipe yield must be positive")
             
        factor = actual_units / recipe.yield_quantity
        
        for item in recipe.items:
             quantity_needed = item.quantity * factor
             # Add waste factor? (Net -> Gross) or just consumption?
             # Planning says "consumo por item = item.quantity * fator * (1 + waste_factor)"
             quantity_needed = quantity_needed * (1 + item.waste_factor)
             
             # Check Balance
             current_balance = inventory_service.get_balance(db, item.ingredient_id)
             if current_balance < quantity_needed:
                  raise ValueError(f"Insufficient stock for ingredient ID {item.ingredient_id}. Need {quantity_needed}, have {current_balance}")
             
             # Prepare deduction logic
             # We need current COST of ingredient to freeze it
             # In MVP, cost is fixed in Ingredient.cost_per_unit.
             # FUTURE: Weighted Average Cost.
             unit_cost = item.ingredient.cost_per_unit
             total_for_item = quantity_needed * unit_cost
             total_cost += total_for_item
             
             stock_deductions.append({
                 "ingredient_id": item.ingredient_id,
                 "quantity": quantity_needed,
                 "unit_cost": unit_cost
             })

        # Execution Pass
        consumptions = []
        for ded in stock_deductions:
             # Create OUT movement
            inventory_service.create_movement(
                db,
                InventoryMovementCreate(
                    ingredient_id=ded["ingredient_id"],
                    type=MovementTypeEnum.OUT,
                    quantity=ded["quantity"],
                    unit_cost_at_time=ded["unit_cost"], # Optional for OUT but good for tracking
                    note=f"Production Batch {batch.code}"
                ),
                user_id
            )
            
            # Create Consumption Record
            cons = BatchConsumption(
                batch_id=batch.id,
                ingredient_id=ded["ingredient_id"],
                quantity_used=ded["quantity"],
                unit_cost_at_time=ded["unit_cost"]
            )
            db.add(cons)
            consumptions.append(cons)

        # Update Batch
        batch.status = BatchStatusEnum.PRODUCED
        batch.actual_units = actual_units
        batch.cost_snapshot_total = total_cost
        batch.cost_snapshot_per_unit = total_cost / actual_units if actual_units > 0 else 0
        
        db.commit()
        db.refresh(batch)
        return batch

batch_service = BatchService()
