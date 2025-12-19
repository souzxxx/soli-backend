from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import admin_or_operator, get_current_user
from app.database import get_db
from app.models.batch import Batch
from app.models.user import User
from app.schemas.batch import BatchCreate, BatchProduce, BatchResponse
from app.services.batch_service import batch_service

router = APIRouter()


@router.post("/batches", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: BatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_operator),
):
    try:
        batch = batch_service.create_batch(db, payload, current_user.id)
        return batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/batches", response_model=List[BatchResponse])
def read_batches(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    batches = (
        db.query(Batch)
        .options(joinedload(Batch.consumptions))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return batches


@router.get("/batches/{batch_id}", response_model=BatchResponse)
def read_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    batch = (
        db.query(Batch)
        .options(joinedload(Batch.consumptions))
        .filter(Batch.id == batch_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@router.post("/batches/{batch_id}/produce", response_model=BatchResponse)
def produce_batch(
    batch_id: int,
    payload: BatchProduce,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_operator),
):
    try:
        batch = batch_service.produce_batch(db, batch_id, payload, current_user.id)
        return batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
