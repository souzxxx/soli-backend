from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient, UnitEnum
from app.models.inventory import MovementTypeEnum


@pytest.fixture
def sample_ingredient(db: Session):
    ingredient = Ingredient(name="Flour", unit=UnitEnum.g, cost_per_unit=0.005)
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient

@pytest.fixture
def ingredients(db: Session):
    flour = Ingredient(name="Flour", unit=UnitEnum.g, cost_per_unit=0.005)
    sugar = Ingredient(name="Sugar", unit=UnitEnum.g, cost_per_unit=0.002)
    db.add_all([flour, sugar])
    db.commit()
    db.refresh(flour)
    db.refresh(sugar)
    return {"flour_id": flour.id, "sugar_id": sugar.id}


def test_create_movement_in_and_check_balance(
    client: TestClient, admin_headers: dict, sample_ingredient: Ingredient
):
    payload = {
        "ingredient_id": sample_ingredient.id,
        "type": "IN",
        "quantity": 1000,
        "unit_cost_at_time": 0.005,
        "note": "Initial stock"
    }
    response = client.post("/api/v1/inventory/movements", json=payload, headers=admin_headers)
    assert response.status_code == 201
    
    # Check balance
    resp = client.get(f"/api/v1/inventory/balance/{sample_ingredient.id}", headers=admin_headers)
    assert resp.status_code == 200
    assert float(resp.json()["balance"]) == 1000.0


def test_create_movement_out_insufficient_stock(
    client: TestClient, admin_headers: dict, sample_ingredient: Ingredient
):
    # Try to OUT 100 without stock
    payload = {
        "ingredient_id": sample_ingredient.id,
        "type": "OUT",
        "quantity": 100,
    }
    response = client.post("/api/v1/inventory/movements", json=payload, headers=admin_headers)
    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]


def test_read_movements_filters(
    client: TestClient, admin_headers: dict, ingredients: dict
):
    from datetime import datetime, timedelta
    
    ing_id = ingredients["flour_id"]
    
    # 1. Filter by Ingredient
    resp = client.get(f"/api/v1/inventory/movements?ingredient_id={ing_id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all(m["ingredient_id"] == ing_id for m in data)
    
    # 2. Filter by Date (Empty range should return something if we have data)
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)
    
    resp = client.get(
        f"/api/v1/inventory/movements?start_date={yesterday.isoformat()}&end_date={tomorrow.isoformat()}",
        headers=admin_headers
    )
    assert resp.status_code == 200
    # Should contain recent movements


def test_create_movement_out_success(
    client: TestClient, admin_headers: dict, sample_ingredient: Ingredient
):
    # Add stock first
    payload_in = {
        "ingredient_id": sample_ingredient.id,
        "type": "IN",
        "quantity": 500,
        "unit_cost_at_time": 0.005
    }
    client.post("/api/v1/inventory/movements", json=payload_in, headers=admin_headers)

    # Now OUT
    payload_out = {
        "ingredient_id": sample_ingredient.id,
        "type": "OUT",
        "quantity": 200,
    }
    response = client.post("/api/v1/inventory/movements", json=payload_out, headers=admin_headers)
    assert response.status_code == 201

    # Check balance: 500 - 200 = 300
    resp = client.get(f"/api/v1/inventory/balance/{sample_ingredient.id}", headers=admin_headers)
    assert float(resp.json()["balance"]) == 300.0


def test_adjust_movement(
    client: TestClient, admin_headers: dict, sample_ingredient: Ingredient
):
    # Add stock 100
    client.post(
        "/api/v1/inventory/movements",
        json={"ingredient_id": sample_ingredient.id, "type": "IN", "quantity": 100, "unit_cost_at_time": 1},
        headers=admin_headers
    )

    # Adjust +50
    payload_adj = {
        "ingredient_id": sample_ingredient.id,
        "type": "ADJUST",
        "quantity": 50,
        "unit_cost_at_time": 1,
        "note": "Found more"
    }
    resp = client.post("/api/v1/inventory/movements", json=payload_adj, headers=admin_headers)
    assert resp.status_code == 201

    # Check balance: 100 + 50 = 150
    resp2 = client.get(f"/api/v1/inventory/balance/{sample_ingredient.id}", headers=admin_headers)
    assert float(resp2.json()["balance"]) == 150.0
