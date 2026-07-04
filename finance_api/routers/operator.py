"""Shared operator contract endpoints for Brain/domain communication."""

from __future__ import annotations

import threading
from typing import Any

from fastapi import APIRouter, HTTPException

from finance_api.domains.insights.queries import get_sync_health
from finance_api.domains.sync.monobank import run_sync

router = APIRouter()


def _sync_state() -> dict[str, Any]:
    try:
        return get_sync_health()
    except Exception as exc:  # pragma: no cover - defensive runtime path
        return {"status": "db_unavailable", "error": str(exc)}


def _finance_blockers(sync: dict[str, Any]) -> list[dict[str, Any]]:
    status = sync.get("status")
    if status in {"completed", "running", "never_synced"}:
        return []
    if status == "failed":
        return [
            {
                "id": "finance.sync_failed",
                "severity": "blocked",
                "summary": "Monobank sync failed",
                "needs_human": False,
                "details": sync.get("error"),
            }
        ]
    if status == "db_unavailable":
        return [
            {
                "id": "finance.db_unavailable",
                "severity": "blocked",
                "summary": "Finance database unavailable",
                "needs_human": False,
                "details": sync.get("error"),
            }
        ]
    return [
        {
            "id": "finance.sync_unknown",
            "severity": "warning",
            "summary": f"Unknown sync status: {status or 'missing'}",
            "needs_human": False,
        }
    ]


def _finance_actions() -> list[dict[str, Any]]:
    return [
        {
            "id": "finance.refresh",
            "label": "🔁 Refresh",
            "description": "Run Monobank sync in the background",
            "requires_confirmation": False,
        },
        {
            "id": "finance.recap",
            "label": "💸 Recap",
            "description": "Return current finance operator brief",
            "requires_confirmation": False,
        },
    ]


def _finance_brief() -> dict[str, Any]:
    sync = _sync_state()
    blockers = _finance_blockers(sync)
    status = "blocked" if blockers else "ok"
    sync_status = sync.get("status", "unknown")
    if blockers:
        summary = blockers[0]["summary"]
    elif sync_status == "running":
        summary = "Finance sync is running"
    elif sync_status == "never_synced":
        summary = "Finance core healthy. No sync has run yet."
    else:
        summary = "Finance core healthy. No blocker."
    return {
        "domain": "finance",
        "status": status,
        "summary": summary,
        "highlights": [],
        "blockers": blockers,
        "actions": _finance_actions(),
        "sync": sync,
    }


@router.get("/brief")
def brief() -> dict[str, Any]:
    """Return compact domain state for Brain aggregation."""
    return _finance_brief()


@router.get("/blockers")
def blockers() -> dict[str, Any]:
    """Return current Finance blockers only."""
    sync = _sync_state()
    return {"domain": "finance", "blockers": _finance_blockers(sync)}


@router.get("/actions")
def actions() -> dict[str, Any]:
    """Return available Finance actions for Brain/buttons."""
    return {"domain": "finance", "actions": _finance_actions()}


@router.post("/actions/{action_id}")
def run_action(action_id: str) -> dict[str, Any]:
    """Execute a safe Finance action requested by Brain."""
    if action_id == "finance.refresh":
        threading.Thread(target=run_sync, daemon=True).start()
        return {
            "domain": "finance",
            "action": action_id,
            "status": "started",
            "summary": "Finance refresh started",
        }
    if action_id == "finance.recap":
        return _finance_brief()
    raise HTTPException(status_code=404, detail=f"Unknown action: {action_id}")