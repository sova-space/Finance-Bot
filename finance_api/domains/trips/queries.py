"""Trips domain queries."""

import uuid
from typing import Any

import structlog
from sqlmodel import Session, select

from finance_api.domains.trips.models import Trip

log = structlog.get_logger(__name__)


def list_trips(session: Session) -> list[dict[str, Any]]:
    """Return all trips."""
    trips = session.exec(select(Trip)).all()
    return [_to_dict(t) for t in trips]


def get_trip(session: Session, trip_id: uuid.UUID) -> Trip | None:
    """Return a single Trip by ID, or None if not found."""
    return session.get(Trip, trip_id)


def create_trip(
    session: Session,
    name: str,
    budget: float | None,
    currency: str,
    start_date: Any,
    end_date: Any,
    notes: str | None,
) -> dict[str, Any]:
    """Insert a new trip and return its dict representation."""
    trip = Trip(
        name=name,
        budget=budget,
        currency=currency,
        start_date=start_date,
        end_date=end_date,
        notes=notes,
    )
    session.add(trip)
    session.commit()
    session.refresh(trip)
    log.info("trip_created", trip_id=str(trip.id), name=name)
    return _to_dict(trip)


def update_trip(
    session: Session,
    trip_id: uuid.UUID,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Apply partial updates to a trip. Returns None if not found."""
    trip = session.get(Trip, trip_id)
    if trip is None:
        return None
    for field, value in updates.items():
        setattr(trip, field, value)
    session.add(trip)
    session.commit()
    session.refresh(trip)
    return _to_dict(trip)


def delete_trip(session: Session, trip_id: uuid.UUID) -> bool:
    """Delete a trip by ID. Returns False if not found."""
    trip = session.get(Trip, trip_id)
    if trip is None:
        return False
    session.delete(trip)
    session.commit()
    return True


def _to_dict(trip: Trip) -> dict[str, Any]:
    return {
        "id": str(trip.id),
        "name": trip.name,
        "budget": trip.budget,
        "currency": trip.currency,
        "start_date": trip.start_date.isoformat(),
        "end_date": trip.end_date.isoformat(),
        "notes": trip.notes,
        "created_at": trip.created_at.isoformat(),
    }
