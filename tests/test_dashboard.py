from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.batch import Batch, BatchStatusEnum
from app.models.ingredient import Ingredient, UnitEnum
from app.models.inventory import InventoryMovement, MovementTypeEnum
from app.models.recipe import Recipe, RecipeItem


@pytest.fixture
def dashboard_setup(db: Session):
    # Setup for stats verification
    # 1. Ingredient: High value, low stock
    saffron = Ingredient(name="Saffron", unit=UnitEnum.g, cost_per_unit=50.0, active=True)
    
    # 2. Ingredient: Low value, high stock
    water = Ingredient(name="Water", unit=UnitEnum.g, cost_per_unit=0.01, active=True)
    
    db.add_all([saffron, water])
    db.commit()
    db.refresh(saffron)
    db.refresh(water)
    
    # Add Movements
    # Saffron: 5g IN (Value: 250)
    m1 = InventoryMovement(ingredient_id=saffron.id, type=MovementTypeEnum.IN, quantity=5, unit_cost_at_time=50, created_by=1)
    # Water: 1000g IN (Value: 10)
    m2 = InventoryMovement(ingredient_id=water.id, type=MovementTypeEnum.IN, quantity=1000, unit_cost_at_time=0.01, created_by=1)
    
    db.add_all([m1, m2])
    db.commit()
    
    # Create a Batch (Production Cost)
    # Mock Batch directly
    recipe = Recipe(name="Soup", yield_quantity=10, yield_unit=UnitEnum.g)
    db.add(recipe)
    db.flush()
    
    batch = Batch(
        code="TEST-BATCH",
        recipe_id=recipe.id,
        status=BatchStatusEnum.PRODUCED,
        planned_units=10,
        actual_units=10,
        cost_snapshot_total=100.0, # Mock cost
        created_by=1
    )
    db.add(batch)
    db.commit()
    
    return {"saffron": saffron, "water": water}

def test_dashboard_stats(
    client: TestClient, admin_headers: dict, dashboard_setup: dict
):
    response = client.get("/api/v1/dashboard/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Total Inventory Value:
    # Saffron: 5 * 50 = 250
    # Water: 1000 * 0.01 = 10
    # Total = 260
    assert float(data["total_inventory_value"]) == 260.0
    
    # Monthly Production Cost
    assert float(data["monthly_production_cost"]) == 100.0
    
    # Total Products Produced
    assert float(data["total_products_produced"]) == 10.0


def test_dashboard_alerts(
    client: TestClient, admin_headers: dict, dashboard_setup: dict
):
    # Saffron has 5g. Threshold 10. Should alert.
    # Water has 1000g. Threshold 10. Should NOT alert.
    
    response = client.get("/api/v1/dashboard/alerts?threshold=10", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) >= 1
    alert_names = [a["name"] for a in data]
    assert "Saffron" in alert_names
    assert "Water" not in alert_names
