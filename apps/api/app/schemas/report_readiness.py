from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel


ReportReadinessOverallStatus = Literal["ready", "needs_attention", "blocked"]
ReportReadinessCheckStatus = Literal["pass", "warning", "fail"]
ReportReadinessSeverity = Literal["low", "medium", "high"]
ReportReadinessGroup = Literal[
    "Required",
    "Supporting Evidence",
    "Open Issues",
    "Draft / Communication Context",
]


class ReportReadinessCheck(BaseModel):
    key: str
    label: str
    group: ReportReadinessGroup
    status: ReportReadinessCheckStatus
    severity: ReportReadinessSeverity
    message: str
    related_count: int | None = None
    suggested_next_step: str | None = None


class ReportReadinessResponse(BaseModel):
    job_id: uuid.UUID
    overall_status: ReportReadinessOverallStatus
    score: int | None = None
    summary: str
    checks: list[ReportReadinessCheck]
    blockers: list[ReportReadinessCheck]
    warnings: list[ReportReadinessCheck]
    ready_items: list[ReportReadinessCheck]
