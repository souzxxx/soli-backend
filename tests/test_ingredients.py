from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient, UnitEnum


def test_create_ingredient_admin(client: TestClient, admin_headers: dict):
    payload = {
        "name": "Flour",
        "unit": "g",
        "cost_per_unit": 0.005,
        "supplier_name": "Test Supplier"
    }
    response = client.post("/api/v1/ingredients", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Flour"
    assert data["unit"] == "g"
    assert data["id"] is not None


def test_create_ingredient_operator(client: TestClient, operator_headers: dict):
    payload = {
        "name": "Sugar",
        "unit": "g",
        "cost_per_unit": 0.002,
    }
    response = client.post("/api/v1/ingredients", json=payload, headers=operator_headers)
    assert response.status_code == 201


def test_read_ingredients(client: TestClient, admin_headers: dict, db: Session):
    ingredient = Ingredient(name="Milk", unit=UnitEnum.ml, cost_per_unit=0.01)
    db.add(ingredient)
    db.commit()

    response = client.get("/api/v1/ingredients", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Milk"


def test_update_ingredient(client: TestClient, admin_headers: dict, db: Session):
    ingredient = Ingredient(name="Butter", unit=UnitEnum.g, cost_per_unit=0.05)
    db.add(ingredient)
    db.commit()

    payload = {"cost_per_unit": 0.06}
    response = client.patch(f"/api/v1/ingredients/{ingredient.id}", json=payload, headers=admin_headers)
    assert response.status_code == 200
    assert float(response.json()["cost_per_unit"]) == 0.06


def test_delete_ingredient(client: TestClient, admin_headers: dict, db: Session):
    ingredient = Ingredient(name="Eggs", unit=UnitEnum.un, cost_per_unit=0.5)
    db.add(ingredient)
    db.commit()

    response = client.delete(f"/api/v1/ingredients/{ingredient.id}", headers=admin_headers)
    assert response.status_code == 204

    # Verify soft delete (active=False)
    db.refresh(ingredient)
    assert ingredient.active is False


def test_delete_ingredient_operator_forbidden(client: TestClient, operator_headers: dict, db: Session):
    ingredient = Ingredient(name="Salt", unit=UnitEnum.g, cost_per_unit=0.001)
    db.add(ingredient)
    db.commit()

    response = client.delete(f"/api/v1/ingredients/{ingredient.id}", headers=operator_headers)
    assert response.status_code == 403
