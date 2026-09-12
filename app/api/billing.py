from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user, require_teacher
from app.domain.models import User, Invoice

router = APIRouter(prefix="/billing", tags=["Billing & Invoices"])


class InvoiceCreateRequest(BaseModel):
    student_id: int
    title: str
    amount: float          # frontend sends 'amount', stored as total_amount
    currency: Optional[str] = "USD"
    due_date: Optional[str] = None


class UpdateInvoiceStatusRequest(BaseModel):
    status: str            # 'paid', 'unpaid', 'pending'


def _invoice_dict(inv: Invoice, include_student: bool = False) -> dict:
    """Shared serialiser — always uses total_amount column."""
    d = {
        "id": inv.id,
        "student_id": inv.student_id,
        "title": inv.title,
        "amount": float(inv.total_amount or 0),          # backward-compat key
        "total_amount": float(inv.total_amount or 0),
        "paid_amount": float(inv.paid_amount or 0),
        "currency": inv.currency,
        "status": inv.status,
        "due_date": str(inv.due_date) if inv.due_date else None,
        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }
    if include_student:
        d["student_name"] = inv.student.name if inv.student else ""
        d["student_code"] = inv.student.student_code if inv.student else ""
    return d


@router.post("/invoices")
def create_invoice(
    payload: InvoiceCreateRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    due_date_obj = datetime.strptime(payload.due_date, "%Y-%m-%d").date() if payload.due_date else None
    new_invoice = Invoice(
        student_id=payload.student_id,
        title=payload.title,
        total_amount=payload.amount,
        paid_amount=0.00,
        currency=payload.currency or "USD",
        status="unpaid",
        due_date=due_date_obj,
    )
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)
    return {"success": True, "invoice_id": new_invoice.id}


@router.get("/invoices")
def get_invoices(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role in ["teacher", "admin"]:
        invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
        return [_invoice_dict(inv, include_student=True) for inv in invoices]
    else:
        # Strict isolation: student sees only their own invoices
        invoices = (
            db.query(Invoice)
            .filter(Invoice.student_id == user.id)
            .order_by(Invoice.created_at.desc())
            .all()
        )
        return [_invoice_dict(inv) for inv in invoices]


@router.patch("/invoices/{invoice_id}/status")
def update_invoice_status(
    invoice_id: int,
    payload: UpdateInvoiceStatusRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="រកមិនឃើញវិក្កយបត្រនេះទេ")

    if payload.status not in ("paid", "unpaid", "pending"):
        raise HTTPException(status_code=400, detail="status ត្រូវជា paid, unpaid, ឬ pending")

    inv.status = payload.status
    inv.paid_at = datetime.utcnow() if payload.status == "paid" else None
    db.commit()
    db.refresh(inv)
    return {"success": True, "status": inv.status, "paid_at": inv.paid_at}


@router.delete("/invoices/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="រកមិនឃើញវិក្កយបត្រនេះទេ")

    db.delete(inv)
    db.commit()
    return {"success": True, "message": "បានលុបវិក្កយបត្រដោយជោគជ័យ"}
