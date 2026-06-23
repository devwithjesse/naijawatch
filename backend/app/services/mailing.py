import smtplib
from email.message import EmailMessage

from ..core.config import settings


class Mailer:
    @staticmethod
    def send_email(to: str, subject: str, html: str) -> bool:
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            print("[EMAIL ERROR] SMTP credentials not set in environment.")
            return False
    
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = settings.FROM_EMAIL
            msg["To"] = to
    
            msg.set_content(html, subtype="html")
    
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                smtp.send_message(msg)
    
            return True
        except Exception as e:
            print(f"[EMAIL ERROR] {e}")
            return False
