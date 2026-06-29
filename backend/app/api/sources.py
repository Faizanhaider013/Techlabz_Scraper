"""Sources endpoint: included / skipped sources and reasons."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Source
from app.schemas import SourceOut

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    sources = db.execute(select(Source).order_by(Source.status, Source.name)).scalars().all()
    return [SourceOut.model_validate(s) for s in sources]
