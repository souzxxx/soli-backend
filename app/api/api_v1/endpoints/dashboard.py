from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardStatsResponse, LowStockAlert
from app.services.dashboard_service import dashboard_service

router = APIRouter()


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stats = dashboard_service.get_stats(db)
    return stats


@router.get("/dashboard/alerts", response_model=List[LowStockAlert])
def get_low_stock_alerts(
    threshold: float = 10.0,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    alerts = dashboard_service.get_low_stock_alerts(db, threshold)
    return alerts
