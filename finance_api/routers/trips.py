"""Trips endpoints."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlmodel import Session

from finance_api.core.auth.webapp import verify_webapp_user
from finance_api.core.db.engine import get_session
from finance_api.domains.insights.queries import get_spending_by_category
from finance_api.domains.trips import queries

router = APIRouter(
    prefix="/trips",
    tags=["trips"],
    dependencies=[Depends(verify_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]


class TripCreate(BaseModel):
    """Request body for creating a trip."""

    name: str
    budget: float | None = None
    currency: str = "UAH"
    start_date: date
    end_date: date
    notes: str | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "TripCreate":
        """Enforce end_date >= start_date at the application layer."""
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


class TripPatch(BaseModel):
    """Request body for updating a trip."""

    name: str | None = None
    budget: float | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "TripPatch":
        """Enforce end_date >= start_date when both are provided."""
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be >= start_date")
        return self


@router.get("", summary="List trips")
def list_trips(session: SessionDep) -> list[dict]:
    """Return all trips."""
    return queries.list_trips(session)


@router.post("", summary="Create a trip")
def create_trip(body: TripCreate, session: SessionDep) -> dict:
    """Create a new trip."""
    return queries.create_trip(
        session,
        name=body.name,
        budget=body.budget,
        currency=body.currency,
        start_date=body.start_date,
        end_date=body.end_date,
        notes=body.notes,
    )


@router.get("/{trip_id}/spending", summary="Trip spending breakdown")
def get_trip_spending(trip_id: uuid.UUID, session: SessionDep) -> list[dict]:
    """Return spending by category scoped to the trip's date range."""
    trip = queries.get_trip(session, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return get_spending_by_category(start=trip.start_date, end=trip.end_date)


@router.patch("/{trip_id}", summary="Update a trip")
def patch_trip(trip_id: uuid.UUID, body: TripPatch, session: SessionDep) -> dict:
    """Partially update a trip."""
    updates: dict = {}
    for field in ("name", "budget", "currency", "start_date", "end_date", "notes"):
        value = getattr(body, field)
        if value is not None:
            updates[field] = value

    result = queries.update_trip(session, trip_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return result


@router.delete("/{trip_id}", summary="Delete a trip")
def delete_trip(trip_id: uuid.UUID, session: SessionDep) -> dict:
    """Delete a trip. Returns 404 if not found."""
    if not queries.delete_trip(session, trip_id):
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"deleted": True}
