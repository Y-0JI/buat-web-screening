import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import urljoin

from app.config import settings

logger = logging.getLogger(__name__)

RESET_PATH = "/reset-password"


def build_reset_link(token: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}{RESET_PATH}?token={token}"


def _send_smtp(to_email: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def send_reset_email(to_email: str, token: str) -> None:
    """Kirim email tautan reset password.

    Menggunakan mekanisme pengiriman yang sama (satu sumber konfigurasi
    SMTP di `settings`) untuk seluruh alur autentikasi. Bila SMTP belum
    dikonfigurasi, tautan dicatat ke log agar alur tetap bisa diuji di
    environment development.
    """
    link = build_reset_link(token)
    subject = "BSJP AI — Reset Password Anda"
    body = (
        "Halo,\n\n"
        "Kami menerima permintaan untuk mereset password akun BSJP AI Anda.\n"
        "Klik tautan berikut untuk membuat password baru (berlaku 1 jam):\n\n"
        f"{link}\n\n"
        "Jika Anda tidak meminta reset password, abaikan email ini.\n"
        "Tautan hanya dapat digunakan satu kali.\n"
    )

    if settings.smtp_host:
        try:
            _send_smtp(to_email, subject, body)
            logger.info("Email reset password dikirim ke %s", to_email)
            return
        except Exception as e:  # noqa: BLE001 - fallback ke log saat SMTP gagal
            logger.warning("Gagal mengirim email reset ke %s: %s", to_email, e)

    logger.info(
        "SMTP belum dikonfigurasi — tautan reset untuk %s: %s", to_email, link
    )
