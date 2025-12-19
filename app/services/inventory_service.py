from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryMovement, MovementTypeEnum
from app.schemas.inventory import InventoryMovementCreate


class InventoryService:
    def get_balance(self, db: Session, ingredient_id: int) -> Decimal:
        """
        Calculate current balance for an ingredient.
        Formula: Sum(IN) + Sum(ADJUST) - Sum(OUT)
        Assuming ADJUST quantity is signed (positive adds, negative removes).
        IN and OUT quantities are absolute (should be positive).
        """
        # Sum quantities grouped by type
        stmt = (
            select(
                InventoryMovement.type,
                func.sum(InventoryMovement.quantity).label("total"),
            )
            .where(InventoryMovement.ingredient_id == ingredient_id)
            .group_by(InventoryMovement.type)
        )
        results = db.execute(stmt).all()

        total_in = Decimal(0)
        total_out = Decimal(0)
        total_adjust = Decimal(0)

        for type_, total in results:
            if total is None:
                continue
            if type_ == MovementTypeEnum.IN:
                total_in = total
            elif type_ == MovementTypeEnum.OUT:
                total_out = total
            elif type_ == MovementTypeEnum.ADJUST:
                total_adjust = total

        # Balance = IN - OUT + ADJUST
        # We assume OUT quantity is stored as positive but represents subtraction.
        return total_in - total_out + total_adjust

    def create_movement(
        self, db: Session, movement_in: InventoryMovementCreate, user_id: int
    ) -> InventoryMovement:
        # Check constraints
        if movement_in.type == MovementTypeEnum.OUT:
            current_balance = self.get_balance(db, movement_in.ingredient_id)
            if current_balance < movement_in.quantity:
                raise ValueError("Insufficient stock for this OUT movement.")
        
        # Determine cost validation
        if movement_in.type in [MovementTypeEnum.IN, MovementTypeEnum.ADJUST]:
             if movement_in.unit_cost_at_time is None:
                 # It might be optional in schema, but business logic requires it or defaults it?
                 # Planning says: "IN/ADJUST devem exigir unit_cost_at_time"
                 # But schema allows None? I should probably enforce it here or let it be 0.
                 # If None, I'll raise error as per planning.
                 raise ValueError("unit_cost_at_time is required for IN/ADJUST movements.")

        db_obj = InventoryMovement(
            ingredient_id=movement_in.ingredient_id,
            type=movement_in.type,
            quantity=movement_in.quantity,
            unit_cost_at_time=movement_in.unit_cost_at_time,
            note=movement_in.note,
            created_by=user_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

inventory_service = InventoryService()
