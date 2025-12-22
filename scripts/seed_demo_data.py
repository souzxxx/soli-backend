import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models.batch import Batch, BatchConsumption, BatchStatusEnum
from app.models.ingredient import Ingredient, UnitEnum
from app.models.inventory import InventoryMovement, MovementTypeEnum
from app.models.recipe import Recipe, RecipeItem
from app.models.user import RoleEnum, User


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_data():
    db = SessionLocal()
    
    # 0. RAW CLEANUP (Avoid Enum Validation Errors)
    # Since we removed 'kg' and 'l' from the python enum, SQLAlchemy will crash if it tries to load rows with those values.
    # We must delete them via raw SQL first.
    from sqlalchemy import text
    try:
        print("Pre-cleaning deprecated units via SQL...")
        db.execute(text("DELETE FROM inventory_movements WHERE ingredient_id IN (SELECT id FROM ingredients WHERE unit IN ('kg', 'l'))"))
        db.execute(text("DELETE FROM batch_consumptions WHERE ingredient_id IN (SELECT id FROM ingredients WHERE unit IN ('kg', 'l'))"))
        db.execute(text("DELETE FROM recipe_items WHERE ingredient_id IN (SELECT id FROM ingredients WHERE unit IN ('kg', 'l'))"))
        db.execute(text("DELETE FROM ingredients WHERE unit IN ('kg', 'l')"))
        db.commit()
    except Exception as e:
        print(f"Warning during raw cleanup: {e}")
        db.rollback()

    # 1. Ensure Admin User
    admin = db.query(User).filter(User.email == "admin@solidifica.com").first()
    if not admin:
        # Check if old admin exists and update or create new
        old_admin = db.query(User).filter(User.email == "admin@soli.com").first()
        local_admin = db.query(User).filter(User.email == "admin@solidifica.local").first()
        
        if old_admin:
            print("Renaming old admin to new domain...")
            old_admin.email = "admin@solidifica.com"
            admin = old_admin
        elif local_admin:
             print("Fixing local admin domain...")
             local_admin.email = "admin@solidifica.com"
             admin = local_admin
        else:
            admin = User(
                email="admin@solidifica.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Admin Solidifica",
                role=RoleEnum.ADMIN,
            )
            db.add(admin)
        
        db.commit()
        db.refresh(admin)
        print(f"Admin User: {admin.email}")
    else:
        print(f"Admin exists: {admin.email}")

    # 1.5 CLEANUP OLD DATA (Confectionery)
    print("Cleaning up legacy confectionery data...")
    legacy_recipes = ["Bolo de Cenoura com Chocolate", "Bolo de Chocolate Simples", "Brioche Amanteigado"]
    for r_name in legacy_recipes:
        rec = db.query(Recipe).filter(Recipe.name == r_name).first()
        if rec:
            # Delete dependent batches and their consumptions
            batches = db.query(Batch).filter(Batch.recipe_id == rec.id).all()
            for b in batches:
                 db.query(BatchConsumption).filter(BatchConsumption.batch_id == b.id).delete()
                 db.delete(b) 
            
            db.query(RecipeItem).filter(RecipeItem.recipe_id == rec.id).delete()
            db.delete(rec)
            print(f"Deleted legacy recipe: {r_name}")
    
    legacy_ingredients = [
        "Trigo (Farinha)", "Açúcar Refinado", "Ovos (Cartela 30)", "Leite Integral", 
        "Manteiga Extra", "Chocolate em Pó 50%", "Fermento Químico", "Essência de Baunilha", 
        "Sal", "Cenoura", "Óleo de Soja"
    ]
    for i_name in legacy_ingredients:
        ing = db.query(Ingredient).filter(Ingredient.name == i_name).first()
        if ing:
            db.query(InventoryMovement).filter(InventoryMovement.ingredient_id == ing.id).delete()
            db.delete(ing)
            print(f"Deleted legacy ingredient: {i_name}")
    
    db.commit()

    # 2. Ingredients for Solid Cosmetics (CONVERTED TO G/ML)
    ingredients_data = [
        # Oils & Butters
        # Cost per ml/g: Divide KG/L price by 1000
        {"name": "Azeite de Oliva Extra Virgem", "unit": UnitEnum.ml, "cost": 0.035}, # 35.00/L
        {"name": "Óleo de Coco", "unit": UnitEnum.ml, "cost": 0.045}, # 45.00/L
        {"name": "Manteiga de Karité", "unit": UnitEnum.g, "cost": 0.085}, # 85.00/kg
        {"name": "Óleo de Rícino (Mamona)", "unit": UnitEnum.ml, "cost": 0.050}, # 50.00/L
        {"name": "Manteiga de Cacau", "unit": UnitEnum.g, "cost": 0.090}, # 90.00/kg
        
        # Base Chemicals
        {"name": "Soda Cáustica (Hidróxido de Sódio) 99%", "unit": UnitEnum.g, "cost": 0.015}, # 15.00/kg
        
        # Additives & Exfoliants
        {"name": "Carvão Ativado em Pó", "unit": UnitEnum.g, "cost": 0.25}, # 250/kg
        {"name": "Argila Branca", "unit": UnitEnum.g, "cost": 0.08}, # 80/kg
        {"name": "Aveia em Flocos Finos", "unit": UnitEnum.g, "cost": 0.012}, # 12.00/kg
        
        # Scents (Essential Oils) - Already ml
        {"name": "Óleo Essencial de Lavanda", "unit": UnitEnum.ml, "cost": 0.80},
        {"name": "Óleo Essencial de Melaleuca (Tea Tree)", "unit": UnitEnum.ml, "cost": 0.70},
        {"name": "Óleo Essencial de Laranja Doce", "unit": UnitEnum.ml, "cost": 0.40},
        {"name": "Óleo Essencial de Capim Limão", "unit": UnitEnum.ml, "cost": 0.50},

        # Packaging
        {"name": "Papel Seda para Sabonete", "unit": UnitEnum.un, "cost": 0.20},
        {"name": "Etiqueta Kraft Redonda", "unit": UnitEnum.un, "cost": 0.15},
        {"name": "Barbante de Sisal", "unit": UnitEnum.un, "cost": 0.10},
    ]
    
    created_ingredients = {}
    for data in ingredients_data:
        ing = db.query(Ingredient).filter(Ingredient.name == data["name"]).first()
        if not ing:
            ing = Ingredient(
                name=data["name"],
                unit=data["unit"],
                cost_per_unit=data["cost"],
                active=True
            )
            db.add(ing)
            db.commit()
            db.refresh(ing)
            print(f"Created Ingredient: {ing.name}")
        else:
             # Update definition if exists to ensure units are correct
             ing.unit = data["unit"]
             ing.cost_per_unit = data["cost"]
             db.commit()
             
        created_ingredients[ing.name] = ing

    # 3. Initial Inventory (Stock)
    # Simulate Date: 1 month ago
    base_date = datetime.utcnow() - timedelta(days=30)
    
    for name, ing in created_ingredients.items():
        # Check if already has stock to avoid dupes on re-run
        has_moves = db.query(InventoryMovement).filter(InventoryMovement.ingredient_id == ing.id).first()
        if not has_moves:
            qty = random.randint(1000, 5000) # 1kg - 5kg
            if ing.unit == UnitEnum.un:
                qty = 500
            
            move = InventoryMovement(
                ingredient_id=ing.id,
                type=MovementTypeEnum.IN,
                quantity=qty,
                unit_cost_at_time=ing.cost_per_unit,
                note="Estoque Inicial - Doação/Compra",
                created_by=admin.id,
                created_at=base_date
            )
            db.add(move)
            print(f"Stocked {qty} {ing.unit.value} of {ing.name}")
    db.commit()

    # 4. Recipes
    recipes_def = [
        {
            "name": "Sabonete Lavanda Relaxante (Barra)",
            "yield": 10, "unit": UnitEnum.un, # 10 Barras de ~100g
            "items": [
                {"ing": "Azeite de Oliva Extra Virgem", "qty": 500}, # 500ml
                {"ing": "Óleo de Coco", "qty": 200}, # 200ml
                {"ing": "Soda Cáustica (Hidróxido de Sódio) 99%", "qty": 100}, # 100g
                {"ing": "Óleo Essencial de Lavanda", "qty": 10}, # 10ml
                {"ing": "Argila Branca", "qty": 15}, # 15g
                {"ing": "Papel Seda para Sabonete", "qty": 10},
                {"ing": "Etiqueta Kraft Redonda", "qty": 10},
            ]
        },
        {
            "name": "Shampoo Sólido Detox (Carvão)",
            "yield": 12, "unit": UnitEnum.un,
            "items": [
                 {"ing": "Manteiga de Karité", "qty": 300}, # 300g
                 {"ing": "Óleo de Coco", "qty": 200}, # 200ml
                 {"ing": "Óleo de Rícino (Mamona)", "qty": 100}, # 100ml
                 {"ing": "Soda Cáustica (Hidróxido de Sódio) 99%", "qty": 80}, # 80g
                 {"ing": "Carvão Ativado em Pó", "qty": 20}, # 20g
                 {"ing": "Óleo Essencial de Melaleuca (Tea Tree)", "qty": 15}, # 15ml
                 {"ing": "Papel Seda para Sabonete", "qty": 12},
                 {"ing": "Etiqueta Kraft Redonda", "qty": 12},
            ]
        },
        {
            "name": "Condicionador Sólido Hidratação Profunda",
            "yield": 15, "unit": UnitEnum.un,
            "items": [
                 {"ing": "Manteiga de Cacau", "qty": 500}, # 500g
                 {"ing": "Manteiga de Karité", "qty": 300}, # 300g
                 {"ing": "Óleo de Rícino (Mamona)", "qty": 100}, # 100ml
                 {"ing": "Óleo Essencial de Laranja Doce", "qty": 20}, # 20ml
                 {"ing": "Papel Seda para Sabonete", "qty": 15},
                 {"ing": "Etiqueta Kraft Redonda", "qty": 15},
            ]
        }
    ]

    created_recipes = []
    for r_def in recipes_def:
        rec = db.query(Recipe).filter(Recipe.name == r_def["name"]).first()
        if not rec:
            rec = Recipe(
                name=r_def["name"],
                yield_quantity=r_def["yield"],
                yield_unit=r_def["unit"]
            )
            db.add(rec)
            db.flush()
            
            for item in r_def["items"]:
                ing_obj = created_ingredients.get(item["ing"])
                if ing_obj:
                    r_item = RecipeItem(
                        recipe_id=rec.id,
                        ingredient_id=ing_obj.id,
                        quantity=item["qty"],
                        waste_factor=0.0
                    )
                    db.add(r_item)
            
            db.commit()
            print(f"Created Recipe: {rec.name}")
        created_recipes.append(rec)

    # 5. Production History (Batches)
    
    # Check if we have batches to avoid over-populating
    batch_count = db.query(Batch).count()
    if batch_count > 5:
        print("Batches already exist, skipping mass generation.")
        return

    print("Generating Production History...")
    for i in range(15):
        # Random date in last 30 days
        days_ago = random.randint(1, 30)
        batch_date = datetime.utcnow() - timedelta(days=days_ago)
        
        recipe = random.choice(created_recipes)
        planned_multipler = random.choice([1, 2, 3]) # 1x, 2x or 3x the recipe yield
        planned_units = int(recipe.yield_quantity) * planned_multipler
        
        # Determine status
        status = random.choice([BatchStatusEnum.PLANNED, BatchStatusEnum.PRODUCED, BatchStatusEnum.PRODUCED])
        
        batch = Batch(
            code=f"LOTE-{batch_date.strftime('%Y%m%d')}-{i:02d}",
            recipe_id=recipe.id,
            status=status,
            planned_units=planned_units,
            created_by=admin.id,
            created_at=batch_date
        )
        
        if status == BatchStatusEnum.PRODUCED:
            batch.actual_units = planned_units # Perfect production
            # Calculate cost
            total_cost = 0
            # Deduct Inventory & Create Consumption
            factor = planned_units / float(recipe.yield_quantity)
            
            for item in recipe.items:
                required_qty = float(item.quantity) * factor
                cost_at_time = float(item.ingredient.cost_per_unit)
                total_cost += required_qty * cost_at_time
                
                # Consume
                cons = BatchConsumption(
                    batch_id=batch.id, # Access via flush later, or add to relationship via append
                    ingredient_id=item.ingredient_id,
                    quantity_used=required_qty,
                    unit_cost_at_time=item.ingredient.cost_per_unit
                )
                batch.consumptions.append(cons)
                
                # Inventory OUT
                move = InventoryMovement(
                    ingredient_id=item.ingredient_id,
                    type=MovementTypeEnum.OUT,
                    quantity=required_qty,
                    note=f"Produção {batch.code}",
                    created_by=admin.id,
                    created_at=batch_date
                )
                db.add(move)
            
            batch.cost_snapshot_total = total_cost
            batch.cost_snapshot_per_unit = total_cost / planned_units if planned_units > 0 else 0

        db.add(batch)
    
    db.commit()
    print("Seed Completo! Dados de cosméticos sólidos gerados (Unidades revisadas).")


if __name__ == "__main__":
    seed_data()
