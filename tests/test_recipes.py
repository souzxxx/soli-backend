from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient, UnitEnum
from app.models.recipe import Recipe


@pytest.fixture
def ingredients_setup(db: Session):
    # Flour: 0.005 per g
    flour = Ingredient(name="Flour", unit=UnitEnum.g, cost_per_unit=0.005)
    # Sugar: 0.002 per g
    sugar = Ingredient(name="Sugar", unit=UnitEnum.g, cost_per_unit=0.002)
    # Eggs: 0.50 per un
    eggs = Ingredient(name="Eggs", unit=UnitEnum.un, cost_per_unit=0.50)
    
    db.add_all([flour, sugar, eggs])
    db.commit()
    db.refresh(flour)
    db.refresh(sugar)
    db.refresh(eggs)
    return {"flour": flour, "sugar": sugar, "eggs": eggs}


def test_create_recipe(
    client: TestClient, admin_headers: dict, ingredients_setup: dict
):
    payload = {
        "name": "Cake",
        "yield_quantity": 1,
        "yield_unit": "un",
        "items": [
            {
                "ingredient_id": ingredients_setup["flour"].id,
                "quantity": 500,
                "waste_factor": 0
            },
            {
                "ingredient_id": ingredients_setup["eggs"].id,
                "quantity": 3,
                "waste_factor": 0
            }
        ]
    }
    response = client.post("/api/v1/recipes", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Cake"
    assert len(data["items"]) == 2


def test_calculate_recipe_cost(
    client: TestClient, admin_headers: dict, ingredients_setup: dict
):
    # Create Recipe first
    # Cost should be:
    # Flour: 500g * 0.005 = 2.50
    # Sugar: 200g * 0.002 = 0.40
    # Eggs: 3un * 0.50 = 1.50
    # Total: 4.40
    
    payload = {
        "name": "Sweet Cake",
        "yield_quantity": 2, # Yields 2 cakes
        "yield_unit": "un",
        "items": [
            {"ingredient_id": ingredients_setup["flour"].id, "quantity": 500},
            {"ingredient_id": ingredients_setup["sugar"].id, "quantity": 200},
            {"ingredient_id": ingredients_setup["eggs"].id, "quantity": 3},
        ]
    }
    create_resp = client.post("/api/v1/recipes", json=payload, headers=admin_headers)
    recipe_id = create_resp.json()["id"]

    # Get Cost
    response = client.get(f"/api/v1/recipes/{recipe_id}/cost", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["total_cost"]) == 4.40
    assert float(data["yield_quantity"]) == 2.0
    assert float(data["cost_per_unit"]) == 2.20 # 4.40 / 2


def test_add_item_to_recipe(
    client: TestClient, admin_headers: dict, ingredients_setup: dict
):
    # Create empty recipe
    payload = {
        "name": "Bread",
        "yield_quantity": 1,
        "yield_unit": "un",
        "items": []
    }
    create_resp = client.post("/api/v1/recipes", json=payload, headers=admin_headers)
    recipe_id = create_resp.json()["id"]

    # Add item
    item_payload = {
        "ingredient_id": ingredients_setup["flour"].id,
        "quantity": 1000,
        "waste_factor": 0.1
    }
    response = client.post(f"/api/v1/recipes/{recipe_id}/items", json=item_payload, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert float(data["items"][0]["quantity"]) == 1000
