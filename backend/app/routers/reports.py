"""
reports.py — trigger + poll analysis runs.

A report is an async job (BackgroundTasks) because the full pipeline takes
~60-90s. The frontend POSTs to create, then polls GET /reports/{id} until the
status is 'done', then reads result_json (the preserved 10-module dict).

For production robustness a real queue (Celery/RQ + Redis) can replace
BackgroundTasks without changing the API contract.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from ..db import SessionLocal, get_db
from ..models import Client, ClientAccess, Report, ReportStatus, Role, User
from ..schemas import ReportCreate, ReportOut
from ..security.sessions import get_current_user
from ..services import reports as report_service
from ..services.credentials import client_ga4_property_id, resolve_credential

router = APIRouter(prefix="/reports", tags=["reports"])


def _authorized(db: DbSession, user: User, client: Client) -> bool:
    if user.role == Role.admin or client.owner_user_id == user.id:
        return True
    return db.query(ClientAccess).filter(
        ClientAccess.user_id == user.id, ClientAccess.client_id == client.id
    ).count() > 0


def _run_job(report_id: str, days: int, model: str, analyst_name: str,
             end_date: str | None = None, start_date: str | None = None,
             prev_start: str | None = None, prev_end: str | None = None) -> None:
    """Background worker — owns its own DB session (request session is closed)."""
    db = SessionLocal()
    try:
        report = db.get(Report, report_id)
        if report is None:
            return
        report.status = ReportStatus.running
        db.commit()

        client = db.get(Client, report.client_id)
        client_cfg = {
            "use_demo_data": client.use_demo_data,
            "ga4_property_id": client_ga4_property_id(client),
            "gsc_site_url": client.gsc_site_url,
            "organic_only": client.organic_only,
        }
        credential = resolve_credential(client)

        results = report_service.run_report(
            client_cfg, credential, days, model, analyst_name,
            end_date=end_date, start_date=start_date,
            prev_start=prev_start, prev_end=prev_end,
        )
        report.result_json = json.dumps(results, default=str)
        report.status = ReportStatus.done
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        report = db.get(Report, report_id)
        if report:
            report.status = ReportStatus.failed
            report.error = str(exc)
            db.commit()
    finally:
        db.close()


@router.post("", response_model=ReportOut, status_code=status.HTTP_202_ACCEPTED)
def create_report(body: ReportCreate, background: BackgroundTasks,
                  user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    client = db.get(Client, body.client_id)
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")
    if not _authorized(db, user, client):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this client")

    # Resolve the effective window: a custom start/end range takes precedence
    # over `days`. days = inclusive length of the range.
    days = body.days
    end_date = body.end_date
    start_date = body.start_date
    prev_start = body.compare_start
    prev_end = body.compare_end
    if start_date and end_date:
        import datetime as _dt
        try:
            s = _dt.date.fromisoformat(start_date)
            e = _dt.date.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Dates must be YYYY-MM-DD")
        if e < s:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "end_date is before start_date")
        days = (e - s).days + 1

    report = Report(
        client_id=client.id, requested_by=user.id, status=ReportStatus.pending,
        params_json=json.dumps({"days": days, "start_date": start_date, "end_date": end_date,
                                "compare_start": prev_start, "compare_end": prev_end, "model": body.model}),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background.add_task(_run_job, report.id, days, body.model, user.name, end_date, start_date, prev_start, prev_end)
    return ReportOut(id=report.id, client_id=client.id, status=report.status.value)


@router.get("/{report_id}")
def get_report(report_id: str, user: User = Depends(get_current_user),
               db: DbSession = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    client = db.get(Client, report.client_id)
    if not _authorized(db, user, client):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    out: dict = {"id": report.id, "client_id": report.client_id,
                 "status": report.status.value, "error": report.error}
    if report.status == ReportStatus.done and report.result_json:
        out["results"] = json.loads(report.result_json)
    return out
