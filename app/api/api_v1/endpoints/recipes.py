from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import admin_or_operator, get_current_user
from app.database import get_db
from app.models.recipe import Recipe, RecipeItem
from app.models.user import User
from app.schemas.recipe import (
    RecipeCostResponse,
    RecipeCreate,
    RecipeItemCreate,
    RecipeResponse,
    RecipeUpdate,
)
from app.services.recipe_service import recipe_service

router = APIRouter()


@router.post("/recipes", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: RecipeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_or_operator),
):
    # Check name uniqueness
    existing = db.query(Recipe).filter(Recipe.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Recipe with this name already exists")
    
    recipe = recipe_service.create_recipe(db, payload)
    return recipe


@router.get("/recipes", response_model=List[RecipeResponse])
def read_recipes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    recipes = (
        db.query(Recipe)
        .options(joinedload(Recipe.items))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return recipes


@router.get("/recipes/{recipe_id}", response_model=RecipeResponse)
def read_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    recipe = (
        db.query(Recipe)
        .options(joinedload(Recipe.items))
        .filter(Recipe.id == recipe_id)
        .first()
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.patch("/recipes/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: int,
    payload: RecipeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_or_operator),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(recipe, key, value)

    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("/recipes/{recipe_id}/cost", response_model=RecipeCostResponse)
def get_recipe_cost(
    recipe_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cost_response = recipe_service.calculate_cost(db, recipe_id)
    if not cost_response:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return cost_response


@router.post("/recipes/{recipe_id}/items", response_model=RecipeResponse)
def add_recipe_item(
    recipe_id: int,
    payload: RecipeItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_or_operator),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Check if item exists
    existing = db.query(RecipeItem).filter(
        RecipeItem.recipe_id == recipe_id, 
        RecipeItem.ingredient_id == payload.ingredient_id
    ).first()
    
    if existing:
        # Update existing
        existing.quantity = payload.quantity
        existing.waste_factor = payload.waste_factor
    else:
        # Create new
        item = RecipeItem(
            recipe_id=recipe_id,
            ingredient_id=payload.ingredient_id,
            quantity=payload.quantity,
            waste_factor=payload.waste_factor
        )
        db.add(item)
    
    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/recipes/{recipe_id}/items/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe_item(
    recipe_id: int,
    ingredient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_or_operator),
):
    item = db.query(RecipeItem).filter(
        RecipeItem.recipe_id == recipe_id,
        RecipeItem.ingredient_id == ingredient_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    db.delete(item)
    db.commit()
    return None
