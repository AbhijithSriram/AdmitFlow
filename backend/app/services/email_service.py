import html
import smtplib
from email.message import EmailMessage

from flask import current_app

from app.services import content_service


def demo_footer_html() -> str:
    """Added to every email while DEMO_MODE is on: emails reach people outside the website, so they
    must say what AdmitFlow is. Empty on a real deployment."""
    if not content_service.demo_mode():
        return ""
    name = html.escape(content_service.institution_name())
    return (
        '<hr style="border:none;border-top:1px solid #ddd;margin-top:24px">'
        f'<p style="font-size:12px;color:#666">AdmitFlow is an academic project, and {name} is fictional. '
        "This is not an email from any real college, and no admission is offered. "
        "Payments run in test mode; no real money is charged.</p>"
    )


def _send(to_address: str, subject: str, html_body: str, attachments: list[tuple[str, bytes, str]] | None = None) -> None:
    """Send an HTML email via smtplib, optionally with attachments as (filename, content, mime_subtype).
    Every email gets the academic-project footer while DEMO_MODE is on (demo_footer_html)."""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = current_app.config["SMTP_USERNAME"]
    message["To"] = to_address
    message.set_content("This email requires an HTML-capable client.")
    message.add_alternative(html_body + demo_footer_html(), subtype="html")

    for filename, content, mime_subtype in attachments or []:
        message.add_attachment(content, maintype="application", subtype=mime_subtype, filename=filename)

    with smtplib.SMTP(current_app.config["SMTP_HOST"], current_app.config["SMTP_PORT"]) as smtp:
        smtp.starttls()
        smtp.login(current_app.config["SMTP_USERNAME"], current_app.config["SMTP_PASSWORD"])
        smtp.send_message(message)


def send_otp_email(to_address: str, otp: str) -> None:
    _send(to_address, "Your AdmitFlow verification code", f"<p>Your OTP is <b>{otp}</b>. It expires in 10 minutes.</p>")


def send_password_reset_email(to_address: str, otp: str) -> None:
    _send(to_address, "AdmitFlow password reset", f"<p>Your password reset OTP is <b>{otp}</b>.</p>")


def send_payment_confirmation_email(
    to_address: str, pdf_bytes: bytes, receipt_bytes: bytes, context: dict | None = None
) -> None:
    context = context or {}
    name = html.escape(str(context.get("full_name") or "Applicant"))
    programme = context.get("programme")
    programme_line = f" for <b>{html.escape(str(programme))}</b>" if programme else ""

    body = (
        f"<p>Dear {name},</p>"
        f"<p>Your AdmitFlow application{programme_line} has been received and your payment "
        "has been confirmed.</p>"
        "<p>Your completed application and payment receipt are attached to this email.</p>"
    )

    _send(
        to_address,
        "AdmitFlow application confirmed",
        body,
        attachments=[
            ("application.pdf", pdf_bytes, "pdf"),
            ("receipt.pdf", receipt_bytes, "pdf"),
        ],
    )
