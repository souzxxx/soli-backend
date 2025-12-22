from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import admin_only, admin_or_operator, get_current_user
from app.database import get_db
from app.models.ingredient import Ingredient
from app.models.user import User
from app.schemas.ingredient import (
    IngredientCreate,
    IngredientResponse,
    IngredientUpdate,
)

router = APIRouter()


# Endpoint PÚBLICO para a vitrine (sem autenticação)
@router.get("/ingredients/public", response_model=List[IngredientResponse])
def read_public_ingredients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Lista ingredientes ativos para exibição pública na vitrine."""
    return db.query(Ingredient).filter(Ingredient.active == True).offset(skip).limit(limit).all()


@router.post(
    "/ingredients", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED
)
def create_ingredient(
    payload: IngredientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_or_operator),
):
    ingredient = Ingredient(**payload.model_dump())
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.get("/ingredients", response_model=List[IngredientResponse])
def read_ingredients(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Ingredient)
    if active_only:
        query = query.filter(Ingredient.active == True)
    return query.offset(skip).limit(limit).all()


@router.get("/ingredients/{ingredient_id}", response_model=IngredientResponse)
def read_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return ingredient


@router.patch("/ingredients/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(
    ingredient_id: int,
    payload: IngredientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_or_operator),
):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ingredient, key, value)

    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.delete("/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    # Soft delete
    ingredient.active = False
    db.commit()
    return None
