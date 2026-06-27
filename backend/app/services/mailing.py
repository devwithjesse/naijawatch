import resend

from ..core.config import settings

resend.api_key = settings.RESEND_API_KEY


class Mailer:
    @staticmethod
    def send_email(to: str, subject: str, html: str) -> bool:
        try:
            resend.Emails.send(
                {
                    "from": settings.FROM_EMAIL,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "reply_to": settings.REPLY_TO,
                }
            )
            return True

        except Exception as e:
            print(f"[EMAIL ERROR] {e}")
            return False