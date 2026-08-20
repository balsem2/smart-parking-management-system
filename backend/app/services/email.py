import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_password_reset_email(email: str, username: str, reset_link: str) -> bool:
    host = os.getenv("SMTP_HOST")
    if not host:
        logger.warning("SMTP_HOST is not configured; reset email was not sent to %s", email)
        return False

    port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = "".join(os.getenv("SMTP_PASSWORD", "").split())
    sender = os.getenv("SMTP_FROM", smtp_user or "no-reply@smartpark.local")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    message = EmailMessage()
    message["Subject"] = "Set your SmartPark password"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"Hello {username},\n\n"
        "Your SmartPark account has been created. Use the link below to set your password:\n\n"
        f"{reset_link}\n\n"
        "If you did not expect this email, contact your SmartPark administrator."
    )

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            if use_tls:
                smtp.starttls()
            if smtp_user and smtp_password:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("Could not send password reset email to %s", email)
        return False

    return True
