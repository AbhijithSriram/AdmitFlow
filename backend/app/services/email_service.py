import smtplib
from email.message import EmailMessage

from flask import current_app


def _send(to_address: str, subject: str, html_body: str, attachments: list[tuple[str, bytes, str]] | None = None) -> None:
    """Send an HTML email via smtplib, optionally with attachments as (filename, content, mime_subtype)."""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = current_app.config["SMTP_USERNAME"]
    message["To"] = to_address
    message.set_content("This email requires an HTML-capable client.")
    message.add_alternative(html_body, subtype="html")

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


def send_payment_confirmation_email(to_address: str, pdf_bytes: bytes, receipt_bytes: bytes) -> None:
    _send(
        to_address,
        "AdmitFlow application confirmed",
        "<p>Your application and payment have been confirmed. See attachments.</p>",
        attachments=[
            ("application.pdf", pdf_bytes, "pdf"),
            ("receipt.pdf", receipt_bytes, "pdf"),
        ],
    )
