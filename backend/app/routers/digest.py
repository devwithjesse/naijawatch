import secrets
import smtplib
from datetime import datetime
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database import get_db
from ..services.mailing import Mailer
from ..models import DigestSubscriber
from ..schemas import SubscribeRequest

router = APIRouter()

FROM_EMAIL = settings.FROM_EMAIL
APP_BASE_URL = settings.APP_BASE_URL
APP_NAME = settings.APP_NAME


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def _send_email(to: str, subject: str, html: str) -> bool:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("[EMAIL ERROR] SMTP credentials not set in environment.")
        return False

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = to

        msg.set_content(html, subtype="html")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)

        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


@router.post("/subscribe", status_code=200)
def subscribe(payload: SubscribeRequest, db: Session = Depends(get_db)):
    """
    Description: Initiate newsletter subscription.
    Details: Accepts an email address, generates unique secure tokens for confirmation and
    unsubscription, saves the pending subscriber to the database, and dispatches a confirmation email.
    """
    email = payload.email.lower().strip()
    existing = db.query(DigestSubscriber).filter_by(email=email).first()

    if existing is not None and existing.confirmed is not None:
        raise HTTPException(status_code=400, detail="Already subscribed.")

    confirmation_token = _generate_token()
    unsubscribe_token = _generate_token()

    if existing:
        existing.confirmation_token = confirmation_token
        subscriber = existing
    else:
        subscriber = DigestSubscriber(
            email=email,
            confirmation_token=confirmation_token,
            unsubscribe_token=unsubscribe_token,
        )
        db.add(subscriber)

    db.commit()

    confirm_url = f"{settings.APP_BASE_URL}/confirm?token={confirmation_token}"
    html = f"<h2>Welcome to {APP_NAME}</h2><p>Please <a href='{confirm_url}'>confirm your subscription</a> to receive weekly security digests.</p>"

    if Mailer.send_email(email, f"Confirm your {APP_NAME} subscription", html):
        return {"message": "Confirmation email sent."}
    else:
        return {"message": "Failed to send email, please try again."}


@router.get("/confirm", status_code=200)
def confirm(token: str = Query(...), db: Session = Depends(get_db)):
    """
    Description: Confirm a pending subscription.
    Details: Accepts a token query parameter (usually clicked from an email). If valid, marks the
    subscriber as confirmed so they can begin receiving the weekly digest.
    """
    sub = db.query(DigestSubscriber).filter_by(confirmation_token=token).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Invalid token.")

    sub.confirmed = True
    sub.confirmed_at = datetime.now()
    db.commit()
    return {"message": "Subscription confirmed!"}


@router.get("/unsubscribe", status_code=200)
def unsubscribe(token: str = Query(...), db: Session = Depends(get_db)):
    sub = db.query(DigestSubscriber).filter_by(unsubscribe_token=token).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Invalid token.")

    db.delete(sub)
    db.commit()
    return {"message": "Unsubscribed successfully."}
