from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.runtime.alerts import (
    diagnose_runtime_alert,
    list_runtime_alerts,
    run_runtime_scan,
    runtime_alert_response,
    runtime_status,
    update_alert_status,
)

router = APIRouter()


class AlertStatusRequest(BaseModel):
    status: str
    linked_audit_id: str | None = None


@router.get("/alerts")
def runtime_alerts() -> dict:
    return list_runtime_alerts()


@router.get("/status")
def runtime_scheduler_status() -> dict:
    return runtime_status()


@router.post("/scan")
def runtime_scan() -> dict:
    items = run_runtime_scan(trigger="manual")
    return runtime_alert_response(items)


@router.post("/alerts/{event_id}/status")
def set_runtime_alert_status(event_id: str, request: AlertStatusRequest) -> dict:
    return update_alert_status(event_id, request.status, request.linked_audit_id)


@router.post("/alerts/{event_id}/diagnose")
def diagnose_alert(event_id: str) -> dict:
    return diagnose_runtime_alert(event_id)


@router.post("/signals/{event_id}/diagnose")
def diagnose_signal(event_id: str) -> dict:
    return diagnose_runtime_alert(event_id)
