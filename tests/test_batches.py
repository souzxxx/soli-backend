from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.batch import BatchStatusEnum
from app.models.ingredient import Ingredient, UnitEnum
from app.models.recipe import Recipe, RecipeItem


@pytest.fixture
def ingredients_setup(db: Session):
    flour = Ingredient(name="Flour", unit=UnitEnum.g, cost_per_unit=0.005)
    sugar = Ingredient(name="Sugar", unit=UnitEnum.g, cost_per_unit=0.002)
    db.add_all([flour, sugar])
    db.commit()
    db.refresh(flour)
    db.refresh(sugar)
    return {"flour": flour, "sugar": sugar}


@pytest.fixture
def recipe_setup(db: Session, ingredients_setup: dict):
    recipe = Recipe(name="Batch Cake", yield_quantity=1, yield_unit=UnitEnum.un)
    db.add(recipe)
    db.flush()
    
    # 500g Flour, 200g Sugar
    i1 = RecipeItem(recipe_id=recipe.id, ingredient_id=ingredients_setup["flour"].id, quantity=500, waste_factor=0)
    i2 = RecipeItem(recipe_id=recipe.id, ingredient_id=ingredients_setup["sugar"].id, quantity=200, waste_factor=0)
    db.add_all([i1, i2])
    db.commit()
    db.refresh(recipe)
    return recipe


def test_create_and_produce_batch_flow(
    client: TestClient, admin_headers: dict, ingredients_setup: dict, recipe_setup: Recipe
):
    # 1. Add Stock first
    # Need 500g Flour, 200g Sugar. Let's add 1000g of each.
    client.post(
        "/api/v1/inventory/movements",
        json={"ingredient_id": ingredients_setup["flour"].id, "type": "IN", "quantity": 1000, "unit_cost_at_time": 0.005},
        headers=admin_headers
    )
    client.post(
        "/api/v1/inventory/movements",
        json={"ingredient_id": ingredients_setup["sugar"].id, "type": "IN", "quantity": 1000, "unit_cost_at_time": 0.002},
        headers=admin_headers
    )

    # 2. Plan Batch
    payload_plan = {"recipe_id": recipe_setup.id, "planned_units": 1}
    response = client.post("/api/v1/batches", json=payload_plan, headers=admin_headers)
    assert response.status_code == 201
    batch_id = response.json()["id"]
    assert response.json()["status"] == BatchStatusEnum.PLANNED
    assert response.json()["code"].startswith("SOL-")

    # 3. Produce Batch
    # Execute production of 1 unit
    payload_produce = {"actual_units": 1}
    response = client.post(f"/api/v1/batches/{batch_id}/produce", json=payload_produce, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == BatchStatusEnum.PRODUCED
    assert float(data["actual_units"]) == 1.0
    
    # Verify Cost Snapshot
    # 500*0.005 (2.5) + 200*0.002 (0.4) = 2.9
    assert float(data["cost_snapshot_total"]) == 2.9
    
    # 4. Verify Stock Deduction
    # Flour should be 1000 - 500 = 500
    resp = client.get(f"/api/v1/inventory/balance/{ingredients_setup['flour'].id}", headers=admin_headers)
    assert float(resp.json()["balance"]) == 500.0


def test_produce_batch_insufficient_stock(
    client: TestClient, admin_headers: dict, recipe_setup: Recipe
):
    # Plan Batch
    payload_plan = {"recipe_id": recipe_setup.id, "planned_units": 10} # Needs 5000g flour
    response = client.post("/api/v1/batches", json=payload_plan, headers=admin_headers)
    batch_id = response.json()["id"]
    
    # Try Produce without stock
    response = client.post(f"/api/v1/batches/{batch_id}/produce", json={}, headers=admin_headers)
    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]
