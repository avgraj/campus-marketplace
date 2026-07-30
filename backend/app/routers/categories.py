"""Category routes (plan §9)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from ..database import get_db
from ..models import Category
from ..schemas import CategoryOut

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: OrmSession = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name)).all()
