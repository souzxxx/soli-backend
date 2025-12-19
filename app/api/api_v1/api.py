from fastapi import APIRouter

from app.api.api_v1.endpoints import (
    auth,
    batches,
    dashboard,
    health,
    ingredients,
    inventory,
    recipes,
    users,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(ingredients.router, tags=["ingredients"])
api_router.include_router(inventory.router, tags=["inventory"])
api_router.include_router(recipes.router, tags=["recipes"])
api_router.include_router(batches.router, tags=["batches"])
