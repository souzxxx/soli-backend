from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.security import admin_or_operator, get_current_user
from app.database import get_db
from app.models.ingredient import Ingredient
from app.models.inventory import InventoryMovement
from app.models.user import User
from app.schemas.inventory import (
    InventoryBalanceResponse,
    InventoryMovementCreate,
    InventoryMovementResponse,
)
from app.services.inventory_service import inventory_service

router = APIRouter()


@router.post(
    "/inventory/movements",
    response_model=InventoryMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_movement(
    payload: InventoryMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_operator),
):
    # Verify ingredient exists
    ingredient = db.query(Ingredient).filter(Ingredient.id == payload.ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    try:
        movement = inventory_service.create_movement(
            db=db, movement_in=payload, user_id=current_user.id
        )
        return movement
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inventory/movements", response_model=List[InventoryMovementResponse])
def read_movements(
    ingredient_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(InventoryMovement)
    if ingredient_id:
        query = query.filter(InventoryMovement.ingredient_id == ingredient_id)
    
    if start_date:
        query = query.filter(InventoryMovement.created_at >= start_date)
    
    if end_date:
        query = query.filter(InventoryMovement.created_at <= end_date)
    
    # Order by newest first
    query = query.order_by(desc(InventoryMovement.created_at))
    return query.offset(skip).limit(limit).all()


@router.get("/inventory/balance", response_model=List[InventoryBalanceResponse])
def read_balances(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # This might be heavy if many ingredients. 
    # For now, iterate all ingredients.
    ingredients = db.query(Ingredient).filter(Ingredient.active == True).all()
    results = []
    for ing in ingredients:
        bal = inventory_service.get_balance(db, ing.id)
        results.append(
            InventoryBalanceResponse(
                ingredient_id=ing.id,
                ingredient_name=ing.name,
                balance=bal,
                unit=ing.unit,
                avg_cost=None,  # Not implemented yet
            )
        )
    return results


@router.get("/inventory/balance/{ingredient_id}", response_model=InventoryBalanceResponse)
def read_balance_item(
    ingredient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ing = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ing:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    bal = inventory_service.get_balance(db, ingredient_id)
    return InventoryBalanceResponse(
        ingredient_id=ing.id,
        ingredient_name=ing.name,
        balance=bal,
        unit=ing.unit,
        avg_cost=None,
    )
