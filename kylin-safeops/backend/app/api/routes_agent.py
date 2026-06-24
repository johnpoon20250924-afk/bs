from fastapi import APIRouter
from typing import Any

from pydantic import BaseModel

from backend.app.cognition.diagnosis import diagnose_system_issue

router = APIRouter()


class DiagnoseRequest(BaseModel):
    query: str
    source: dict[str, Any] | None = None


@router.post("/diagnose")
def diagnose(request: DiagnoseRequest) -> dict:
    return diagnose_system_issue(request.query, request.source)
