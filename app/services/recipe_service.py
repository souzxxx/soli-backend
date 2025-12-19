from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeItem
from app.schemas.recipe import (
    ItemCostBreakdown,
    RecipeCostResponse,
    RecipeCreate,
    RecipeItemCreate,
)


class RecipeService:
    def create_recipe(self, db: Session, recipe_in: RecipeCreate) -> Recipe:
        # Create Recipe
        recipe = Recipe(
            name=recipe_in.name,
            yield_quantity=recipe_in.yield_quantity,
            yield_unit=recipe_in.yield_unit,
            notes=recipe_in.notes,
        )
        db.add(recipe)
        db.flush()  # to get ID

        # Create Items
        for item_in in recipe_in.items:
            item = RecipeItem(
                recipe_id=recipe.id,
                ingredient_id=item_in.ingredient_id,
                quantity=item_in.quantity,
                waste_factor=item_in.waste_factor,
            )
            db.add(item)
        
        db.commit()
        db.refresh(recipe)
        return recipe

    def calculate_cost(self, db: Session, recipe_id: int) -> RecipeCostResponse | None:
        recipe = (
            db.query(Recipe)
            .options(joinedload(Recipe.items).joinedload(RecipeItem.ingredient))
            .filter(Recipe.id == recipe_id)
            .first()
        )
        
        if not recipe:
            return None

        breakdown = []
        total_cost = Decimal(0)

        for item in recipe.items:
            unit_cost = item.ingredient.cost_per_unit
            quantity_needed = item.quantity
            
            # TODO: Consider waste_factor logic. 
            # Usually quantity in recipe is "gross quantity" (already includes waste) or "net".
            # If standard recipe implies net, we should divide by (1-waste).
            # For this MVP, let's assume quantity is what is consumed from stock (Gross).
            
            item_total = quantity_needed * unit_cost
            total_cost += item_total
            
            breakdown.append(
                ItemCostBreakdown(
                    ingredient_id=item.ingredient.id,
                    ingredient_name=item.ingredient.name,
                    quantity=quantity_needed,
                    unit=item.ingredient.unit,
                    unit_cost=unit_cost,
                    total_cost=item_total
                )
            )

        cost_per_unit = total_cost / recipe.yield_quantity if recipe.yield_quantity > 0 else Decimal(0)

        return RecipeCostResponse(
            recipe_id=recipe.id,
            recipe_name=recipe.name,
            total_cost=total_cost,
            cost_per_unit=cost_per_unit,
            yield_quantity=recipe.yield_quantity,
            breakdown=breakdown
        )

recipe_service = RecipeService()
